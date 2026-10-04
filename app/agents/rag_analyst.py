"""
RAG / Business Knowledge Analyst Agent.
Interrogates internal corporate knowledge (PDFs/DOCX strategy documents and notes).
Extracts verified facts, management targets, operational context, and policies dynamically.
Never makes causal assertions beyond what is documented.
"""

from __future__ import annotations
import time
from typing import Dict, Any, List, Optional

from app.tools.rag import search_company_knowledge
from app.services.gemini import get_gemini_service
from app.utils.logging import log_agent_step, logger


class RAGAnalystAgent:
    """Specialist agent querying internal corporate business knowledge."""

    def __init__(self):
        self.gemini = get_gemini_service()

    def run(self, question: str, plan_tasks: List[Dict[str, Any]], iteration: int = 0) -> Dict[str, Any]:
        """
        Execute targeted semantic searches over internal knowledge base.
        Returns document citations, evidence objects, and contextual findings.
        """
        start_time = time.perf_counter()
        citations: List[Dict[str, Any]] = []
        evidence_list: List[Dict[str, Any]] = []
        findings: List[Dict[str, Any]] = []

        # 1. Determine search queries dynamically
        search_queries = [question]

        if self.gemini.is_configured():
            try:
                gen_prompt = (
                    f"Generate 2 concise (3-5 words each) search queries to search internal corporate strategy PDFs "
                    f"and policy documents for context to answer: '{question}'. "
                    f"Output only comma-separated queries."
                )
                queries_text = self.gemini.generate_text(gen_prompt, temperature=0.1)
                if queries_text:
                    for q_item in queries_text.split(","):
                        cleaned_q = q_item.strip().strip('"').strip("'")
                        if cleaned_q and len(cleaned_q) > 4:
                            search_queries.append(cleaned_q)
            except Exception as e:
                logger.warning("RAG query generation fallback: %s", e)

        # Keyword heuristics for offline mode
        q_lower = question.lower()
        if "policy" in q_lower or "omnichannel" in q_lower or "discount" in q_lower:
            search_queries.append("Omnichannel retail policy wholesale discounts return thresholds")
        if "chicago" in q_lower or "fulfillment" in q_lower or "2022" in q_lower or "expansion" in q_lower:
            search_queries.append("2022 Q4 expansion performance Chicago fulfillment center")
        if "target" in q_lower or "kpi" in q_lower:
            search_queries.append("Management targets performance KPI definitions")

        with log_agent_step("RAGAnalyst", "Retrieve internal business knowledge", iteration=iteration):
            seen_chunks = set()

            for query in search_queries[:3]:
                search_res = search_company_knowledge(query=query, top_k=3)
                if search_res.get("status") == "success":
                    for item in search_res.get("citations", []):
                        c_id = item["chunk_id"]
                        if c_id not in seen_chunks:
                            seen_chunks.add(c_id)
                            citations.append(item)

                            ev_id = f"EV-DOC-{len(evidence_list)+1:02d}"
                            evidence_list.append({
                                "id": ev_id,
                                "source": item["source_file"],
                                "source_type": "document_passage",
                                "page": item["page"],
                                "details": item["raw_text"][:300] + "...",
                            })

            # 2. Synthesize documented contextual findings dynamically
            for cit in citations[:4]:
                src = cit["source_file"]
                pg = cit["page"]
                txt = cit["raw_text"]

                summary_stmt = ""
                if self.gemini.is_configured():
                    try:
                        sum_prompt = (
                            f"From this document passage (Source: {src}, Page {pg}), extract in 1-2 concise, factual sentences "
                            f"the operational events, policy rules, or management observations relevant to: '{question}'. "
                            f"Do not guess or add external facts.\nPassage:\n{txt}"
                        )
                        summary_stmt = self.gemini.generate_text(sum_prompt, temperature=0.1)
                    except Exception as e:
                        logger.warning("RAG passage summary fallback: %s", e)

                if not summary_stmt or len(summary_stmt) < 20:
                    # Clean first 2 sentences
                    sentences = [s.strip() for s in txt.split(".") if len(s.strip()) > 15]
                    summary_stmt = ". ".join(sentences[:2]) + "." if sentences else txt[:180] + "..."

                title = f"Document Context: {src} (p.{pg})"
                matching_ev = [e["id"] for e in evidence_list if e["source"] == src]

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
