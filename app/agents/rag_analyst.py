"""
RAG / Business Knowledge Analyst Agent.
Interrogates internal corporate knowledge (PDFs/DOCX strategy documents and notes).
Extracts verified facts, management targets, operational context, and policies dynamically.
Never makes causal assertions beyond what is documented.
Optimized for high-speed deterministic retrieval.
"""

from __future__ import annotations
import time
from typing import Dict, Any, List

from app.tools.rag import search_company_knowledge
from app.utils.logging import log_agent_step, logger


class RAGAnalystAgent:
    """Specialist agent querying internal corporate business knowledge."""

    def run(self, question: str, plan_tasks: List[Dict[str, Any]], iteration: int = 0) -> Dict[str, Any]:
        """
        Execute targeted semantic searches over internal knowledge base.
        Returns document citations, evidence objects, and contextual findings instantly.
        """
        start_time = time.perf_counter()
        citations: List[Dict[str, Any]] = []
        evidence_list: List[Dict[str, Any]] = []
        findings: List[Dict[str, Any]] = []

        # 1. High-speed query preparation
        search_queries = [question]
        q_lower = question.lower()

        if "policy" in q_lower or "omnichannel" in q_lower or "discount" in q_lower or "return" in q_lower:
            search_queries.append("Omnichannel policy wholesale discounts return thresholds")
        elif "chicago" in q_lower or "fulfillment" in q_lower or "expansion" in q_lower:
            search_queries.append("Q4 expansion Chicago fulfillment center performance")
        elif "target" in q_lower or "kpi" in q_lower:
            search_queries.append("Corporate management targets and KPI definitions")
        elif "decline" in q_lower or "quarter" in q_lower or "why" in q_lower:
            search_queries.append("Quarterly operational events and supply constraints")

        with log_agent_step("RAGAnalyst", "Retrieve internal business knowledge", iteration=iteration):
            seen_chunks = set()

            for query in search_queries[:2]:
                search_res = search_company_knowledge(query=query, top_k=3)
                if search_res.get("status") == "success":
                    for item in search_res.get("citations", []):
                        c_id = item.get("chunk_id", "")
                        if c_id and c_id not in seen_chunks:
                            seen_chunks.add(c_id)
                            citations.append(item)

                            ev_id = f"EV-DOC-{len(evidence_list)+1:02d}"
                            evidence_list.append({
                                "id": ev_id,
                                "source": item.get("source_file", "unknown"),
                                "source_type": "document_passage",
                                "page": item.get("page", 0),
                                "details": (item.get("raw_text", "")[:300] + "...") if item.get("raw_text") else "No text available",
                            })

            # 2. Extract documented contextual findings instantly without slow LLM loops
            for cit in citations[:4]:
                src = cit.get("source_file", "unknown")
                pg = cit.get("page", 0)
                txt = (cit.get("raw_text") or "").strip()

                # Clean first 2 sentences for immediate evidence statement
                sentences = [s.strip() for s in txt.replace("\n", " ").split(".") if len(s.strip()) > 15]
                summary_stmt = ". ".join(sentences[:2]) + "." if sentences else (txt[:180] + "..." if txt else "Document context retrieved.")

                title = f"Document Context: {src} (p.{pg})"
                matching_ev = [e["id"] for e in evidence_list if e.get("source") == src]

                findings.append({
                    "title": title,
                    "statement": summary_stmt,
                    "metric": None,
                    "value": None,
                    "evidence_ids": matching_ev[:1],
                    "confidence": "Medium",
                    "classification": "evidence",
                })

        duration = time.perf_counter() - start_time
        logger.info("RAGAnalyst completed in %.2fs with %d citations", duration, len(citations))

        return {
            "citations": citations,
            "findings": findings,
            "evidence": evidence_list,
            "duration": round(duration, 3),
        }
