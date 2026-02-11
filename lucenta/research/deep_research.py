import logging
import asyncio
import os
import argparse
from dotenv import load_dotenv

from lucenta.core.workflow.boss_worker import Boss

async def deep_research_workflow(goal: str):
    """
    Orchestrates the Deep Research Workflow: Plan -> Reflect -> Act -> Synthesize.
    Uses the tiered intelligence system for maximum efficiency.
    """
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    boss = Boss()
    
    logging.info(f"Target Goal: {goal}")
    print(f"\n🔬 Initiating Deep Research: {goal}\n")

    # 1. PLAN
    logging.info("Phase 1: Planning...")
    print("Step 1: Planning using Step-Up Model...")
    plan = boss.plan_task(goal)
    
    if not plan:
        logging.error("Planning failed. Aborting.")
        return

    # 2. REFLECT
    logging.info("Phase 2: Validation...")
    print("Step 2: Reflecting on plan logic...")
    is_valid = boss.validate_plan(goal, plan)
    
    if not is_valid:
        logging.warning("Plan has issues. Attempting to repair/replan (placeholder logic).")
        # In a real system, we would loop back to replan with feedback.
        # For this PoC, we proceed with caution or retry once.
        # For now, let's proceed but warn.
        print("⚠️ Plan marked as flawed, but proceeding for demonstration.")
    else:
        print("✅ Plan validated.")

    # 3. ACT (Execute Plan)
    logging.info("Phase 3: Execution...")
    print(f"Step 3: Dispatching {len(plan)} tasks to Workers...")
    results = boss.execute_plan(plan)
    
    # 4. SYNTHESIZE
    logging.info("Phase 4: Synthesis...")
    print("Step 4: Synthesizing final report...")
    final_report = boss.synthesize(goal, results)
    
    print("\n" + "="*50)
    print("📝 FINAL DEEP RESEARCH REPORT")
    print("="*50 + "\n")
    print(final_report)
    print("\n" + "="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lucenta Deep Research Tool")
    parser.add_argument("goal", type=str, help="Research goal or topic")
    args = parser.parse_args()
    
    try:
        asyncio.run(deep_research_workflow(args.goal))
    except KeyboardInterrupt:
        print("\nResearch interrupted.")
