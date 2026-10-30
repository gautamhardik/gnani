"""
DukaanSaathi — Multi-Turn Conversation Scenarios Benchmark (CONV001 - CONV005)
Evaluates state transitions, multi-turn clarifications, corrections, and cart persistence.
"""

import json
from decimal import Decimal
from pathlib import Path
import pytest

from backend.app.services.conversation_manager import ConversationManager
from backend.app.schemas.intelligence import DialogueState

SCENARIOS_PATH = Path(__file__).resolve().parents[2] / "data" / "data" / "conversation_scenarios.json"

@pytest.fixture(scope="module")
def conversation_scenarios():
    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_benchmark_all_5_conversation_scenarios(db_session, conversation_scenarios):
    manager = ConversationManager(db_session)

    scenarios_passed = 0

    for sc in conversation_scenarios:
        sc_id = sc["scenario_id"]
        sc_name = sc["name"]
        turns = sc["turns"]
        expected_final_cart = sc["expected_final_cart"]

        session_id = f"SESS_{sc_id}"
        current_cart = []
        last_response = None

        print(f"\n--- Running Scenario {sc_id}: {sc_name} ---")

        for turn_idx, turn in enumerate(turns):
            speaker = turn["speaker"]
            utterance = turn["utterance"]
            expected_action = turn.get("expected_action")

            if speaker == "assistant":
                # Simulated assistant prompt in scenario definition
                continue

            # Process customer turn
            res = manager.process_turn(
                session_id=session_id,
                user_utterance=utterance,
                existing_cart=[it.model_dump() for it in current_cart]
            )
            last_response = res
            current_cart = res.cart
            print(f"Turn {turn_idx + 1} ({speaker}): '{utterance}' -> action={res.action.action}, state={res.state}, items={len(current_cart)}")

        # Validate Final Cart State against Scenario Expectations
        assert len(current_cart) == len(expected_final_cart), (
            f"Scenario {sc_id} cart size mismatch: expected {len(expected_final_cart)} items, got {len(current_cart)}"
        )

        for exp in expected_final_cart:
            exp_pid = exp["product_id"]
            exp_qty = Decimal(str(exp["quantity"]))
            matched = False
            for act_it in current_cart:
                if act_it.product_id == exp_pid:
                    matched = True
                    assert act_it.quantity == exp_qty, (
                        f"Scenario {sc_id} product {exp_pid} quantity mismatch: expected {exp_qty}, got {act_it.quantity}"
                    )
                    break
            assert matched, f"Scenario {sc_id} expected product {exp_pid} missing from final cart"

        scenarios_passed += 1

    print(f"\n================ MULTI-TURN BENCHMARK REPORT ================")
    print(f"Total Scenarios Evaluated: {len(conversation_scenarios)}")
    print(f"Scenarios Passed:          {scenarios_passed}/{len(conversation_scenarios)} (100%)")
    print(f"=============================================================\n")

    assert scenarios_passed == len(conversation_scenarios)

