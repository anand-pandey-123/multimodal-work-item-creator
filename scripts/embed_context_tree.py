# embed_context_tree.py
import json, chromadb
from sentence_transformers import SentenceTransformer

model      = SentenceTransformer("all-MiniLM-L6-v2")
client     = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("codebase_context")



def load_and_embed(tree_path="context_tree.json"):
    tree = json.load(open(tree_path))

    chunks     = []
    ids        = []
    metadatas  = []

    for module in tree["modules"]:

        # Find owner from team list
        owner = next(
            (m["email"] for m in tree["team"] if module["module_name"] in m["owns"]),
            "unassigned"
        )

        # One chunk per MODULE — high level
        module_text = (
            f"Module: {module['module_name']}. "
            f"Description: {module['description']}. "
            f"Files: {', '.join(f['file'] for f in module['files'])}."
        )
        chunks.append(module_text)
        ids.append(f"module::{module['module_name']}")
        metadatas.append({
            "type":        "module",
            "module_name": module["module_name"],
            "description": module["description"]
        })

        # One chunk per FILE — granular
        for file_info in module["files"]:
            file_text = (
                f"File: {file_info['file']} "
                f"in module '{module['module_name']}'. "
                f"Description: {file_info['description']}. "
            )
            chunks.append(file_text)
            ids.append(f"file::{module['module_name']}::{file_info['file']}")
            metadatas.append({
                "type":        "file",
                "module_name": module["module_name"],
                "file_name":   file_info["file"],
                "description": file_info["description"]
            })

    # Embed all chunks at once
    embeddings = model.encode(chunks, show_progress_bar=True).tolist()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

    print(f"Embedded {len(chunks)} chunks into ChromaDB")


if __name__ == "__main__":
    load_and_embed()