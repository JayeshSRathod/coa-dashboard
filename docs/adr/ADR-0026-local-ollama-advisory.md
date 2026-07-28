# ADR-0026: Local Ollama Advisory Gateway

CQRP may use an operator-selected Ollama model only through the `LLMGateway`
contract and only with a bounded, evidence-cited research packet. The default
remains the deterministic offline gateway. Local Ollama is not a trading,
parameter-tuning, broker, or execution component. Fine-tuning, if ever used,
requires a separate versioned experiment and explicit approval.
