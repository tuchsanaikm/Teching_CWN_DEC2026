#!/usr/bin/env python3
"""
Catalog of visual assets for ReceiptDesk_Slides.html (1 Node x 2x RTX 4090 · NGINX least_conn + 2x vLLM).
All images are centralized under images/ (story/, theory/, lab/, slides/, tests/).
"""

HERO_AND_DIVIDERS = {
    "cover": "images/slides/cover-receiptdesk.jpg",
    "hero_results": "images/slides/h02-lab7-results.jpg",
    "phase_a": "images/slides/d01-phase-a-req.jpg",
    "phase_b": "images/slides/d02-phase-b-plan.jpg",
    "phase_c": "images/slides/d03-phase-c-lab7.jpg",
    "phase_d": "images/slides/d04-phase-d-verify.jpg",
}

EXPLAINERS = {
    "roadmap": "images/slides/x01-roadmap.jpg",
    "gate": "images/slides/x02-gate.jpg",
    "arch_clean": "images/theory/t02-receiptdesk-lab7-arch.jpg",
    "arch_detail": "images/theory/arch-nginx-vllm.png",
    "serving_choice": "images/theory/serving-architecture-choice.png",
    "state_flow": "images/theory/state-flow.png",
    "trace": "images/theory/trace-nginx.png",
}

LIVE_DEMOS = {
    "review_flow": "images/lab/receiptdesk_review_flow.gif",
    "streaming_copilot": "images/lab/receiptdesk_streaming_copilot.gif",
}
