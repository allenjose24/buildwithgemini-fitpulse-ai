# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-03-a9a784fdfd5f"
LOCATION = "us-central1"  # Serverless RAG mode requires us-central1
GCS_PATH = "gs://fitpulse-ai-assets-qwiklabs-gcp-03-a9a784fdfd5f/rag/pg49513.txt"

PARSING_PROMPT = (
    "Extract the individual useful facts, remedies, and descriptions of herbs in this text. "
    "Ignore and omit all boilerplate, license terms, and metadata. "
    "Output clean, self-contained prose."
)


def main():
    print(f"Initializing Vertex AI RAG in project {PROJECT_ID}, location {LOCATION}...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # 1. Switch region RAG managed DB to serverless mode
    cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
    print("Setting RAG Engine config to Serverless mode...")
    try:
        rag.update_rag_engine_config(
            rag_engine_config=rag.RagEngineConfig(
                name=cfg,
                rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
            )
        )
    except Exception as e:
        print(f"Note/Warning on update_rag_engine_config: {e}")

    # 2. Create Corpus
    print("Creating RAG corpus 'fitpulse-gutenberg-corpus'...")
    corpus = rag.create_corpus(
        display_name="fitpulse-gutenberg-corpus",
        embedding_model_config=rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-005"
        ),
    )
    print("Corpus created successfully!")
    print(f"CORPUS_NAME = \"{corpus.name}\"")

    # 3. Import & Index File
    print(f"Importing {GCS_PATH} into corpus...")
    resp = rag.import_files(
        corpus_name=corpus.name,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        llm_parser=rag.LlmParserConfig(
            model_name="gemini-2.5-flash",
            custom_parsing_prompt=PARSING_PROMPT,
        ),
    )
    print(f"Import complete! Imported files count: {resp.imported_rag_files_count}")

    # Write Corpus Name to a local file for tool reference
    with open("rag_corpus_name.txt", "w") as f:
        f.write(corpus.name.strip())
    print("Corpus reference saved to rag_corpus_name.txt")


if __name__ == "__main__":
    main()
