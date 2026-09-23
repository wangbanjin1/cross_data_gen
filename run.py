import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

from src.config import Config

def main():
    parser = argparse.ArgumentParser(description="Cross-Session Memory Dataset Pipeline")
    parser.add_argument("--config", "-c", type=str, default=None, help="Path to config.json")
    parser.add_argument("--input", "-i", type=str, default=None, help="Path to raw personas JSON file (overrides config)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output directory for generated datasets (overrides config)")
    parser.add_argument("--start", "-s", type=int, default=None, help="Start persona index (0-based, overrides config)")
    parser.add_argument("--count", "-n", type=int, default=None, help="Number of personas to generate (overrides config)")
    parser.add_argument("--verify", "-v", action="store_true", help="Run verification across output folder")
    args = parser.parse_args()

    # 如果指定了配置文件，重新加载全局配置
    if args.config:
        Config.load_all(args.config)

    target_output = args.output or Config.output_dir

    if args.verify:
        from scripts.test_verification import main as verify_main
        verify_main(output_dir=target_output)
    else:
        from src.batch_pipeline import BatchPipeline
        pipeline = BatchPipeline(
            output_dir=target_output,
            raw_persona_path=args.input
        )
        pipeline.run_batch(
            start_idx=args.start,
            count=args.count,
            raw_persona_path=args.input
        )

if __name__ == "__main__":
    main()
