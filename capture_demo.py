"""Automated demo flow runner and screenshot capturer using Playwright.
Navigates the Streamlit dashboard on http://127.0.0.1:8501 and records screenshot evidence for all 8 tabs.
"""

import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_evidence", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def main():
    print("Starting automated UI demo and screenshot capture...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()

        print("Navigating to http://127.0.0.1:8501 ...")
        page.goto("http://127.0.0.1:8501")
        page.wait_for_timeout(3500)

        # 1. Load Demo data from sidebar
        print("Clicking Load Demo in sidebar...")
        try:
            demo_btn = page.locator("button:has-text('Load Demo')")
            if demo_btn.count() > 0:
                demo_btn.first.click()
                page.wait_for_timeout(2500)
        except Exception as e:
            print("Note clicking Load Demo:", e)

        # 2. Capture clean default 4-tab view
        clean_view_path = os.path.join(SCREENSHOT_DIR, "00_clean_student_dashboard.png")
        page.screenshot(path=clean_view_path, full_page=False)
        print(f"[OK] Successfully captured {os.path.basename(clean_view_path)}")

        # 3. Enable grading & audit pages for complete evaluation capture
        try:
            toggle_label = page.locator("label:has-text('Show Evaluation & Rubric Tabs')")
            if toggle_label.count() > 0:
                toggle_label.first.click()
                page.wait_for_timeout(2000)
                print("[OK] Enabled Evaluation & Rubric Tabs for evidence capture")
        except Exception as e:
            print("Note toggling audit pages:", e)

        tabs_locator = page.locator('[role="tab"]')
        tab_names = [
            ("01_tab1_add_tasks.png", "Tab 1: Add Tasks"),
            ("02_tab2_prioritized_tracker.png", "Tab 2: Prioritized Tracker"),
            ("03_tab3_conflicts.png", "Tab 3: Conflicts"),
            ("04_tab4_study_plan.png", "Tab 4: AI Study Plan"),
            ("05_tab5_prompt_lab.png", "Tab 5: Prompt Lab"),
            ("06_tab6_validation_tests.png", "Tab 6: Validation & Tests"),
            ("07_tab7_automation_logs.png", "Tab 7: Automation & Logs"),
            ("08_tab8_about_responsible_ai.png", "Tab 8: About & Responsible AI")
        ]

        for idx, (filename, label) in enumerate(tab_names):
            print(f"Navigating to {label} (index {idx})...")
            tabs = page.locator('[role="tab"]').all()
            if idx < len(tabs):
                tabs[idx].click()
                page.wait_for_timeout(2000)

                # Special action per tab to show dynamic results
                if idx == 3:  # Tab 4: Study Plan
                    plan_btn = page.locator("button:has-text('Generate 7-Day Plan')")
                    if plan_btn.count() > 0:
                        plan_btn.first.click()
                        page.wait_for_timeout(2000)

                elif idx == 4:  # Tab 5: Prompt Lab
                    exp_btn = page.locator("button:has-text('Run Prompt Comparison Experiment')")
                    if exp_btn.count() > 0:
                        exp_btn.first.click()
                        page.wait_for_timeout(3000)

                elif idx == 5:  # Tab 6: Validation & Tests
                    test_btn = page.locator("button:has-text('Run All Tests')")
                    if test_btn.count() > 0:
                        test_btn.first.click()
                        page.wait_for_timeout(2500)

                elif idx == 6:  # Tab 7: Automation & Logs
                    sim_btn = page.locator("button:has-text('Simulate Urgent Trigger')")
                    if sim_btn.count() > 0:
                        sim_btn.first.click()
                        page.wait_for_timeout(2500)

                out_path = os.path.join(SCREENSHOT_DIR, filename)
                page.screenshot(path=out_path, full_page=False)
                print(f"[OK] Successfully captured {filename}")

        browser.close()
        print("All 8 tab screenshots captured in test_evidence/screenshots/!")


if __name__ == "__main__":
    main()
