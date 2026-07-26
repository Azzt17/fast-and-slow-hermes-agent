"""

Fase 0 — Uji Round-Trip mem0ai + Chroma Lokal (v2)

LLM: 9router (OpenAI-compatible)   |   Embedder: Ollama lokal (nomic-embed-text)



Prasyarat sebelum menjalankan:

  1. source .venv/bin/activate && pip install "mem0ai[vector-stores]"

  2. export OPENAI_API_KEY="key-9router-kamu"

  3. export OPENAI_BASE_URL="https://endpoint-9router-kamu/v1"

  4. sudo systemctl status ollama   # pastikan Ollama jalan

  5. ollama list                    # pastikan nomic-embed-text sudah ke-pull

"""

import os

from mem0 import Memory



# --- Model LLM dari 9router ---

# Dua opsi yang kamu punya — ganti kalau salah satu tidak bisa dipakai

LLM_MODEL_PRIMARY = "gh/gpt-4o-mini"

LLM_MODEL_FALLBACK = "cx/gpt-5.4-mini"

LLM_MODEL = os.environ.get("MEM0_TEST_LLM_MODEL", LLM_MODEL_PRIMARY)



config = {

    "vector_store": {

        "provider": "chroma",

        "config": {

            "collection_name": "hermes_dual_memory_test",

            "path": "./chroma_db_test",

        },

    },

    "llm": {

        "provider": "openai",

        "config": {

            "model": LLM_MODEL,

            # api_key & base_url sengaja tidak ditulis di sini — dibaca otomatis

            # dari env var OPENAI_API_KEY / OPENAI_BASE_URL yang sudah di-export

        },

    },

    "embedder": {

        "provider": "ollama",

        "config": {

            "model": "nomic-embed-text",

            "ollama_base_url": "http://localhost:11434",

        },

    },

}



TEST_USER = "farid-test"

TEST_FACT = (

    "Proyek hermes-dual-memory memutuskan wrap Mem0 sebagai mesin "

    "retrieval inti, bukan membangun vector search dari nol."

)





def main():

    print(f"=== Konfigurasi: LLM={LLM_MODEL} (9router), Embedder=nomic-embed-text (Ollama lokal) ===")

    try:

        m = Memory.from_config(config)

    except Exception as e:

        print(f"❌ Gagal inisialisasi Memory: {e}")

        print("   Cek: apakah Ollama service jalan? apakah OPENAI_API_KEY/OPENAI_BASE_URL ter-export di shell ini?")

        return



    print("\n=== STEP 1: add() ===")

    try:

        add_result = m.add(

            TEST_FACT,

            user_id=TEST_USER,

            metadata={

                "session_id": "test-session-001",

                "tier": "warm",

                "importance_score": 8,

                "memory_type": "semantic",

            },

        )

        print(add_result)

    except Exception as e:

        print(f"❌ add() gagal: {e}")

        print(f"   Kalau errornya soal model tidak dikenal, coba ganti LLM_MODEL ke '{LLM_MODEL_FALLBACK}'")

        print("   Kalau errornya soal embedding/Ollama, cek: curl http://localhost:11434/api/tags")

        return



    print("\n=== STEP 2: search() ===")

    try:

        search_results = m.search(

            "apa keputusan soal mesin retrieval proyek ini?",

            filters={"user_id": TEST_USER},

        )

        print(search_results)

    except Exception as e:

        print(f"❌ search() gagal: {e}")

        return



    print("\n=== STEP 3: Verifikasi (cek juga isi mentah di atas secara manual) ===")

    raw_str = str(search_results).lower()

    if "mem0" in raw_str or "retrieval" in raw_str:

        print("✅ Indikasi PASS — entri kemungkinan ditemukan kembali lewat search().")

        print("   Konfirmasi manual: apakah teks di STEP 2 di atas memang berisi fakta dari STEP 1?")

    else:

        print("❌ Indikasi FAIL — kata kunci dari fakta asli tidak muncul di hasil search().")

        print("   Cek: apakah add() di STEP 1 sukses tanpa error? Apakah embedder jalan?")



    print("\n=== Cek persistensi disk ===")

    if os.path.isdir("./chroma_db_test"):

        print("✅ Folder ./chroma_db_test ada — data tersimpan ke disk.")

    else:

        print("❌ Folder ./chroma_db_test TIDAK ditemukan — data mungkin cuma in-memory.")





if __name__ == "__main__":

    main()
