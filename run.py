import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Cross-Session Memory Dataset Pipeline")
    parser.add_argument("--start", type=int, default=0, help="Start persona index in original personas (0-based)")
    parser.add_argument("--count", type=int, default=1, help="Number of personas to generate")
    parser.add_argument("--verify", action="store_true", help="Run verification across all generated sample folders")
    args = parser.parse_args()

    if args.verify:
        from scripts.test_verification import main as verify_main
        verify_main()
    else:
        from src.batch_pipeline import BatchPipeline
        pipeline = BatchPipeline()
        pipeline.run_batch(start_idx=args.start, count=args.count)

if __name__ == "__main__":
    main()
