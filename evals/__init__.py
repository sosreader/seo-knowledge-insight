# Laminar offline evaluation scripts for the SEO QA pipeline.
#
# Run all evals:
#   lmnr eval
#
# Run individual evals:
#   python evals/eval_retrieval.py
#   python evals/eval_extraction.py
#   python evals/eval_chat.py   (requires OPENAI_API_KEY + running FastAPI store)
#   python evals/eval_crawled_not_indexed.py   (requires running Hono API at :8002)
