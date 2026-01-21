"""
SOAC End-to-End Demo
====================

Run the complete SOAC pipeline on a real model.
"""

from pathlib import Path
import json
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.orchestrator import run_soac_job, JobConfig


def main():
    # You need to provide an ONNX model file
    # Example: python run_soac_demo.py path/to/your/model.onnx
    
    if len(sys.argv) < 2:
        print("Usage: python run_soac_demo.py <model.onnx> [output_dir]")
        print("\nExample:")
        print("  python run_soac_demo.py resnet18.onnx ./output")
        return 1
    
    model_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("./soac_output")
    
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        return 1
    
    print("=" * 60)
    print("SOAC - Self-Optimizing AI Compiler")
    print("=" * 60)
    print(f"\n📁 Input: {model_path}")
    print(f"📂 Output: {output_dir}\n")
    
    # Configure the job
    config = JobConfig(
        accuracy_threshold=0.02,  # 2% max accuracy drop
        warmup_runs=3,
        measured_runs=10,
        cleanup_on_complete=False,  # Keep artifacts for inspection
    )
    
    # Run the pipeline
    print("🚀 Running SOAC pipeline...\n")
    
    result = run_soac_job(
        uploaded_model_path=model_path,
        config=config,
        work_dir=output_dir,
    )
    
    # Show results
    print("\n" + "=" * 60)
    
    if result.success:
        print("✅ SUCCESS!")
        print(f"\n📊 Selected Variant: {result.selected_variant}")
        print(f"📦 Deployment Bundle: {result.deployment_bundle}")
        
        # Show stage results
        print("\n📋 Stage Results:")
        for stage_result in result.stage_results:
            status = "✓" if stage_result.success else "✗"
            print(f"  {status} {stage_result.stage.value}: {stage_result.duration_ms:.2f}ms")
        
        print(f"\n⏱️  Total Time: {result.total_duration_ms:.2f}ms")
        
    else:
        print("❌ FAILED!")
        print(f"\n🛑 Failed at: {result.final_stage.value}")
        print(f"📛 Error: {result.error.get('message', 'Unknown')}")
    
    # Save full result
    result_path = output_dir / "result.json"
    with open(result_path, 'w') as f:
        json.dump(result.to_dict(), f, indent=2, default=str)
    print(f"\n📄 Full result saved: {result_path}")
    
    # Show logs
    print("\n📜 Logs:")
    for log in result.logs[-10:]:  # Last 10 logs
        print(f"  {log}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    exit(main())
