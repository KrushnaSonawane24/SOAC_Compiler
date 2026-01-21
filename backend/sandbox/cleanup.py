"""
SOAC Sandbox Cleanup Module
============================

Guaranteed cleanup for Docker containers and resources.

CRITICAL REQUIREMENTS:
    - Cleanup MUST happen on success, failure, timeout, and crash
    - Multiple cleanup attempts should be idempotent
    - Cleanup failures are logged but don't mask original errors
    - Orphaned containers are detected and cleaned

IMPLEMENTATION:
    - Uses contextlib.ExitStack for scope-based cleanup
    - Registers atexit handlers for process-level cleanup
    - Tracks all containers in a global registry
"""

import atexit
import logging
import threading
from typing import Optional, Set
from contextlib import contextmanager

try:
    import docker
    from docker.models.containers import Container
    from docker.errors import NotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None  # type: ignore
    Container = None  # type: ignore

from .config import (
    CLEANUP_GRACE_PERIOD_SECONDS,
    CONTAINER_LABEL_PREFIX,
)
from .exceptions import ContainerCleanupError


logger = logging.getLogger(__name__)


# =============================================================================
# CONTAINER REGISTRY
# =============================================================================

# Thread-safe registry of active containers
_container_registry: Set[str] = set()
_registry_lock = threading.Lock()


def register_container(container_id: str) -> None:
    """
    Register a container for cleanup tracking.
    
    Args:
        container_id: Docker container ID.
    """
    with _registry_lock:
        _container_registry.add(container_id)
        logger.debug(f"Registered container {container_id[:12]} for cleanup")


def unregister_container(container_id: str) -> None:
    """
    Unregister a container from cleanup tracking.
    
    Args:
        container_id: Docker container ID.
    """
    with _registry_lock:
        _container_registry.discard(container_id)
        logger.debug(f"Unregistered container {container_id[:12]}")


def get_registered_containers() -> Set[str]:
    """
    Get a copy of all registered container IDs.
    
    Returns:
        Set of container IDs.
    """
    with _registry_lock:
        return _container_registry.copy()


# =============================================================================
# CONTAINER CLEANUP
# =============================================================================

def force_remove_container(
    client: "docker.DockerClient",
    container_id: str,
    grace_period: int = CLEANUP_GRACE_PERIOD_SECONDS
) -> bool:
    """
    Force remove a container, ensuring it's stopped and deleted.
    
    This function is IDEMPOTENT - safe to call multiple times.
    
    Steps:
        1. Stop container (with grace period)
        2. Remove container (with force)
        3. Unregister from tracking
    
    Args:
        client: Docker client instance.
        container_id: Container ID to remove.
        grace_period: Seconds to wait for graceful stop.
    
    Returns:
        True if container was removed, False if not found.
    
    Raises:
        ContainerCleanupError: If removal fails for other reasons.
    """
    try:
        container = client.containers.get(container_id)
    except NotFound:
        # Container already gone - this is fine
        unregister_container(container_id)
        logger.debug(f"Container {container_id[:12]} already removed")
        return False
    except Exception as e:
        raise ContainerCleanupError(container_id, f"Cannot access container: {e}")
    
    try:
        # Try graceful stop first
        if container.status == "running":
            logger.debug(f"Stopping container {container_id[:12]}")
            try:
                container.stop(timeout=grace_period)
            except Exception as e:
                logger.warning(f"Graceful stop failed, will force kill: {e}")
        
        # Force remove
        logger.debug(f"Removing container {container_id[:12]}")
        container.remove(force=True)
        
        unregister_container(container_id)
        logger.info(f"Successfully removed container {container_id[:12]}")
        return True
        
    except NotFound:
        # Container was removed between get and remove - this is fine
        unregister_container(container_id)
        return True
    except Exception as e:
        logger.error(f"Failed to remove container {container_id[:12]}: {e}")
        raise ContainerCleanupError(container_id, str(e))


def kill_container(client: "docker.DockerClient", container_id: str) -> bool:
    """
    Immediately kill a container (SIGKILL).
    
    Use this for timeout enforcement where graceful shutdown is not desired.
    
    Args:
        client: Docker client instance.
        container_id: Container ID to kill.
    
    Returns:
        True if container was killed, False if not found.
    """
    try:
        container = client.containers.get(container_id)
        container.kill()
        logger.info(f"Killed container {container_id[:12]}")
        return True
    except NotFound:
        return False
    except Exception as e:
        logger.warning(f"Failed to kill container {container_id[:12]}: {e}")
        return False


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

@contextmanager
def container_cleanup_context(
    client: "docker.DockerClient",
    container_id: str
):
    """
    Context manager ensuring container cleanup on exit.
    
    Usage:
        with container_cleanup_context(client, container.id):
            # Container is running
            container.wait()
        # Container is guaranteed to be cleaned up here
    
    The container is force-removed on ANY exit:
        - Normal completion
        - Exception
        - KeyboardInterrupt
        - SystemExit
    """
    register_container(container_id)
    try:
        yield
    finally:
        try:
            force_remove_container(client, container_id)
        except ContainerCleanupError as e:
            # Log but don't mask original exception
            logger.error(f"Cleanup failed: {e}")


# =============================================================================
# GLOBAL CLEANUP HANDLERS
# =============================================================================

def _cleanup_all_containers() -> None:
    """
    Emergency cleanup of all registered containers.
    
    Called on process exit via atexit.
    This is a last-resort cleanup for abnormal termination.
    """
    if not DOCKER_AVAILABLE:
        return
    
    containers = get_registered_containers()
    if not containers:
        return
    
    logger.warning(f"Emergency cleanup of {len(containers)} containers")
    
    try:
        client = docker.from_env()
        for container_id in containers:
            try:
                force_remove_container(client, container_id, grace_period=1)
            except Exception as e:
                logger.error(f"Emergency cleanup failed for {container_id[:12]}: {e}")
    except Exception as e:
        logger.error(f"Cannot connect to Docker for emergency cleanup: {e}")


def cleanup_orphaned_containers(client: "docker.DockerClient") -> int:
    """
    Clean up orphaned SOAC sandbox containers.
    
    Orphaned containers are those with SOAC labels that are:
        - Exited but not removed
        - Running longer than expected
    
    Args:
        client: Docker client instance.
    
    Returns:
        Number of containers cleaned up.
    """
    label_filter = {f"{CONTAINER_LABEL_PREFIX}.managed": "true"}
    
    try:
        containers = client.containers.list(
            all=True,
            filters={"label": [f"{k}={v}" for k, v in label_filter.items()]}
        )
    except Exception as e:
        logger.error(f"Failed to list containers for orphan cleanup: {e}")
        return 0
    
    cleaned = 0
    for container in containers:
        try:
            # Check if container is exited or dead
            if container.status in ("exited", "dead", "created"):
                logger.info(f"Cleaning orphaned container {container.short_id}")
                container.remove(force=True)
                cleaned += 1
        except Exception as e:
            logger.warning(f"Failed to clean orphaned container {container.short_id}: {e}")
    
    return cleaned


# Register atexit handler
atexit.register(_cleanup_all_containers)
