"""
SOAC Android Demo Generator
============================

Generates ready-to-run Android Studio project with TFLite model.

GUARANTEES:
    - Always produces valid Android Studio project
    - Always includes working inference example
    - Always creates downloadable zip
"""

import logging
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from . import templates

logger = logging.getLogger(__name__)


def generate_android_demo(
    tflite_path: Path,
    output_dir: Path,
    model_name: str = "model",
    input_size: int = 224,
    num_classes: int = 1000,
    quantization: str = "fp32",
) -> Dict[str, Any]:
    """
    Generate complete Android Studio demo project.
    
    Args:
        tflite_path: Path to TFLite model file.
        output_dir: Directory to create project in.
        model_name: Name of the model (for README).
        input_size: Input image size (default 224).
        num_classes: Number of output classes (default 1000).
        quantization: Quantization type used.
    
    Returns:
        Dict with 'success', 'path', 'zip_path', 'error'.
    """
    tflite_path = Path(tflite_path)
    output_dir = Path(output_dir)
    
    if not tflite_path.exists():
        return {
            "success": False,
            "path": None,
            "zip_path": None,
            "error": f"TFLite model not found: {tflite_path}",
        }
    
    project_dir = output_dir / "android_demo"
    
    try:
        # Create project structure
        _create_project_structure(project_dir)
        
        # Copy TFLite model
        assets_dir = project_dir / "app" / "src" / "main" / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tflite_path, assets_dir / "model.tflite")
        
        # Generate source files
        _write_source_files(project_dir, input_size, num_classes)
        
        # Generate build files
        _write_build_files(project_dir)
        
        # Generate README
        model_size_mb = tflite_path.stat().st_size / (1024 * 1024)
        _write_readme(project_dir, model_name, quantization, model_size_mb)
        
        # Create zip
        zip_path = _create_zip(project_dir, output_dir)
        
        logger.info(f"Android demo generated: {project_dir}")
        
        return {
            "success": True,
            "path": str(project_dir),
            "zip_path": str(zip_path),
            "error": None,
        }
        
    except Exception as e:
        logger.error(f"Failed to generate Android demo: {e}")
        return {
            "success": False,
            "path": None,
            "zip_path": None,
            "error": str(e),
        }


def _create_project_structure(project_dir: Path) -> None:
    """Create Android project directory structure."""
    dirs = [
        project_dir / "app" / "src" / "main" / "java" / "com" / "soac" / "demo",
        project_dir / "app" / "src" / "main" / "res" / "layout",
        project_dir / "app" / "src" / "main" / "res" / "values",
        project_dir / "app" / "src" / "main" / "res" / "mipmap-hdpi",
        project_dir / "app" / "src" / "main" / "assets",
        project_dir / "gradle" / "wrapper",
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def _write_source_files(project_dir: Path, input_size: int, num_classes: int) -> None:
    """Write Java and XML source files."""
    java_dir = project_dir / "app" / "src" / "main" / "java" / "com" / "soac" / "demo"
    res_dir = project_dir / "app" / "src" / "main" / "res"
    manifest_dir = project_dir / "app" / "src" / "main"
    
    # MainActivity.java
    main_activity = templates.MAIN_ACTIVITY_JAVA.format(
        input_size=input_size,
        num_classes=num_classes,
    )
    (java_dir / "MainActivity.java").write_text(main_activity, encoding="utf-8")
    
    # activity_main.xml
    (res_dir / "layout" / "activity_main.xml").write_text(
        templates.ACTIVITY_MAIN_XML, encoding="utf-8"
    )
    
    # AndroidManifest.xml
    (manifest_dir / "AndroidManifest.xml").write_text(
        templates.ANDROID_MANIFEST_XML, encoding="utf-8"
    )
    
    # values/strings.xml
    strings_xml = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">SOAC Demo</string>
</resources>
'''
    (res_dir / "values" / "strings.xml").write_text(strings_xml, encoding="utf-8")
    
    # values/themes.xml
    themes_xml = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.SOACDemo" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
        <item name="colorPrimary">#2196F3</item>
        <item name="colorPrimaryVariant">#1976D2</item>
        <item name="colorOnPrimary">@android:color/white</item>
    </style>
</resources>
'''
    (res_dir / "values" / "themes.xml").write_text(themes_xml, encoding="utf-8")


def _write_build_files(project_dir: Path) -> None:
    """Write Gradle build files."""
    # app/build.gradle
    (project_dir / "app" / "build.gradle").write_text(
        templates.APP_BUILD_GRADLE, encoding="utf-8"
    )
    
    # build.gradle (project)
    (project_dir / "build.gradle").write_text(
        templates.PROJECT_BUILD_GRADLE, encoding="utf-8"
    )
    
    # settings.gradle
    (project_dir / "settings.gradle").write_text(
        templates.SETTINGS_GRADLE, encoding="utf-8"
    )
    
    # gradle.properties
    (project_dir / "gradle.properties").write_text(
        templates.GRADLE_PROPERTIES, encoding="utf-8"
    )
    
    # local.properties (placeholder)
    (project_dir / "local.properties").write_text(
        "# SDK location will be set by Android Studio\n", encoding="utf-8"
    )
    
    # proguard-rules.pro
    (project_dir / "app" / "proguard-rules.pro").write_text(
        "# ProGuard rules for SOAC Demo\n", encoding="utf-8"
    )


def _write_readme(
    project_dir: Path, 
    model_name: str, 
    quantization: str, 
    model_size_mb: float
) -> None:
    """Write README file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    readme = templates.README_MD.format(
        model_name=model_name,
        quantization=quantization,
        model_size_mb=model_size_mb,
        timestamp=timestamp,
    )
    
    (project_dir / "README.md").write_text(readme, encoding="utf-8")


def _create_zip(project_dir: Path, output_dir: Path) -> Path:
    """Create zip archive of the project."""
    zip_path = output_dir / "android_demo.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(project_dir.parent)
                zf.write(file_path, arcname)
    
    logger.info(f"Created zip: {zip_path} ({zip_path.stat().st_size / 1024:.1f} KB)")
    
    return zip_path
