"""
Vera Open — Main orchestrator.

Single entrypoint for all modes:
    python -m src.main --mode daily
    python -m src.main --mode weekly_review
    python -m src.main --mode week_setup
    python -m src.main --mode validate
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

from src.config import load_config, validate_only, VeraConfig
from src.notion import NotionClient

# ============================================================
# Logging setup
# ============================================================

def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s │ %(name)-12s │ %(levelname)-5s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet noisy libraries
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


# ============================================================
# Mode: Daily Briefing
# ============================================================

async def run_daily(config: VeraConfig):
    """
    Full daily pipeline:
    1. Update urgency scores
    2. Collect data from all enabled databases (parallel)
    3. Score & analyze
    4. Build prompt + call AI
    5. Send via Telegram
    """
    start = time.monotonic()
    logger = logging.getLogger("daily")
    logger.info("Starting daily briefing pipeline...")

    async with NotionClient(config.secrets.notion_token) as notion:

        # --- Phase 1: Collect from all enabled databases ---
        logger.info(f"Collecting from: {', '.join(config.enabled_databases)}")

        # Import collectors dynamically based on enabled databases
        from src.tasks import collect_tasks

        # Always collect tasks (required)
        collector_tasks = [collect_tasks(notion, config)]

        # Optional collectors
        if config.daily_check.enabled:
            from src.checks import collect_daily_checks
            collector_tasks.append(collect_daily_checks(notion, config))

        if config.pipeline.enabled:
            from src.pipeline import collect_pipeline
            collector_tasks.append(collect_pipeline(notion, config))

        if config.energy_timing.enabled:
            from src.timing import collect_timing
            collector_tasks.append(collect_timing(notion, config))

        # Run all collectors in parallel
        results = await asyncio.gather(*collector_tasks, return_exceptions=True)

        # Check for collector failures
        collected = {}
        names = ["tasks"] + [
            db for db in ["daily_check", "pipeline", "energy_timing"]
            if getattr(config, db).enabled
        ]
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                logger.error(f"Collector '{name}' failed: {result}")
                collected[name] = None
            else:
                collected[name] = result
                count = len(result) if isinstance(result, list) else "ok"
                logger.info(f"  {name}: {count}")

        if collected.get("tasks") is None:
            logger.error("Tasks collection failed. Cannot generate briefing.")
            return

        # --- Phase 2: Update urgency scores ---
        logger.info("Calculating urgency scores...")
        from src.tasks import update_urgency_scores
        await update_urgency_scores(notion, config, collected["tasks"])

        # --- Phase 3: Score & analyze ---
        logger.info("Running engine (scorer + methodology + auditor)...")
        from src.scorer import calculate_scores
        from src.methodology import prioritize
        from src.auditor import audit_gaps

        scores = calculate_scores(collected, config)
        priorities = prioritize(collected["tasks"], config)
        gaps = audit_gaps(collected, config)

        # --- Phase 4: Build prompt + call AI ---
        logger.info("Synthesizing briefing with AI...")
        from src.synthesize import generate_briefing

        briefing = await generate_briefing(
            config=config,
            collected=collected,
            scores=scores,
            priorities=priorities,
            gaps=gaps,
        )

        # --- Phase 5: Send via Telegram ---
        if config.debug.dry_run:
            logger.info("[DRY RUN] Briefing generated but not sent.")
            logger.info(f"Preview:\n{briefing[:500]}...")
        else:
            from src.telegram import send_briefing
            await send_briefing(config, briefing)
            logger.info("Briefing sent via Telegram ✓")

    elapsed = time.monotonic() - start
    logger.info(f"Daily pipeline completed in {elapsed:.1f}s")


# ============================================================
# Mode: Weekly Review
# ============================================================

async def run_weekly_review(config: VeraConfig):
    """Generate and send weekly review."""
    logger = logging.getLogger("weekly")
    logger.info("Weekly review — not yet implemented (Phase 5)")
    # TODO: Implement in Phase 5


# ============================================================
# Mode: Week Setup
# ============================================================

async def run_week_setup(config: VeraConfig):
    """Set up the upcoming week."""
    logger = logging.getLogger("week_setup")
    logger.info("Week setup — not yet implemented (Phase 5)")
    # TODO: Implement in Phase 5


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Vera Open — Morning OS for Notion users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  validate       Check config.yaml and environment variables
  daily          Run daily briefing pipeline
  weekly_review  Generate weekly review
  week_setup     Set up upcoming week
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly_review", "week_setup", "validate"],
        required=True,
        help="Which pipeline to run",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    args = parser.parse_args()

    # Validate-only mode doesn't need full pipeline
    if args.mode == "validate":
        success = validate_only(args.config)
        sys.exit(0 if success else 1)

    # Load config (validates everything)
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"\n❌ Configuration error:\n   {e}\n")
        print("Run with --mode validate for details.")
        sys.exit(1)

    setup_logging(config.debug.verbose)

    # Dispatch to mode
    mode_map = {
        "daily": run_daily,
        "weekly_review": run_weekly_review,
        "week_setup": run_week_setup,
    }

    try:
        asyncio.run(mode_map[args.mode](config))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        logging.getLogger("vera").error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
