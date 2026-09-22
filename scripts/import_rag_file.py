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

import vertexai
from vertexai.preview import rag

PROJECT_ID = "qwiklabs-gcp-03-a9a784fdfd5f"
LOCATION = "us-central1"
CORPUS_NAME = "projects/1067804430983/locations/us-central1/ragCorpora/150826607051800576"
GCS_PATH = "gs://fitpulse-ai-assets-qwiklabs-gcp-03-a9a784fdfd5f/rag/pg49513.txt"

PARSING_PROMPT = (
    "Extract the individual useful facts, remedies, and descriptions of herbs in this text. "
    "Ignore and omit all boilerplate, license terms, and metadata. "
    "Output clean, self-contained prose."
)


def main():
    print(f"Initializing Vertex AI RAG ({LOCATION})...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    print(f"Importing {GCS_PATH} into corpus {CORPUS_NAME}...")
    resp = rag.import_files(
        corpus_name=CORPUS_NAME,
        paths=[GCS_PATH],
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
        ),
        llm_parser=rag.LlmParserConfig(
            model_name="gemini-2.5-flash",
            custom_parsing_prompt=PARSING_PROMPT,
        ),
    )
    print(f"Import finished successfully! Imported files count: {resp.imported_rag_files_count}")

    with open("rag_corpus_name.txt", "w") as f:
        f.write(CORPUS_NAME)
    print("Saved corpus reference to rag_corpus_name.txt")


if __name__ == "__main__":
    main()
