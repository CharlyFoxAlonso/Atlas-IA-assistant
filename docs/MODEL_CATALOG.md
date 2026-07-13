# 📊 Model Catalog - Atlas v4

Atlas supports a wide range of models across three different execution environments.

## 1. Local Models (Ollama)
These models run on your own hardware, ensuring 100% privacy.

| Model ID | Quality | Recommended Use | Min RAM | Min VRAM |
| :--- | :---: | :--- | :---: | :---: |
| `qwen3:8b` | ⭐⭐⭐ | Fast conversation, simple tasks | 8GB | 6GB |
| `qwen3:14b` | ⭐⭐⭐⭐ | Exams, legal analysis, mid-reasoning | 16GB | 8GB |
| `qwen3:30b-a3b` | ⭐⭐⭐⭐⭐ | **Best Choice.** Coding, deep reasoning, law | 32GB | 10GB |
| `gemma3:12b` | ⭐⭐⭐⭐ | Great Spanish language support | 16GB | 6GB |
| `deepseek-r1:14b` | ⭐⭐⭐⭐⭐ | Complex logic, statistics, CoT | 16GB | 8GB |
| `mistral-small:22b` | ⭐⭐⭐⭐⭐ | High quality, slow speed (CPU friendly) | 32GB | 0GB |
| `phi4:14b` | ⭐⭐⭐⭐ | Math, code, Microsoft-tuned reasoning | 16GB | 8GB |
| `llama3.1:8b` | ⭐⭐⭐ | Fast, strong English capabilities | 8GB | 6GB |

## 2. Cloud Models (NVIDIA NIM)
High-performance industrial models accessed via API.

- **DeepSeek V4 Pro:** Top-tier reasoning and coding.
- **Llama 3.3 70B:** Balanced, extremely versatile.
- **Gemma 4 31B:** Google's latest high-efficiency model.
- **Nemotron 3 Ultra:** Massive scale for ultra-complex tasks.

## 3. Ultra-Fast Models (Groq Cloud)
LPU-accelerated models for near-instantaneous responses.

- **Llama 3.3 70B Versatile:** The gold standard for speed/intelligence.
- **Llama 3.3 8B Instant:** Fastest possible response time.
- **Mixtral 8x7B:** Strong open-weights MoE performance.

---
*Note: Hardware requirements are estimates. Actual performance depends on quantization and OS overhead.*
