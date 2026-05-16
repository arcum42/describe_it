# Phase 7: Semantic Search & RAG Integration

## Overview

Phase 7 introduces optional **Retrieval-Augmented Generation (RAG)** for caption enhancement through semantic similarity search. When enabled, the system can retrieve similar captions from your dataset to use as "few-shot examples" during AI caption generation, improving consistency and quality.

## What is RAG?

RAG combines two capabilities:

1. **Retrieval**: Finding similar existing captions using semantic similarity
2. **Augmented Generation**: Using those examples to guide the AI when generating new captions

This helps the AI understand your dataset's caption style and terminology.

## Requirements

- **ChromaDB** (optional): The semantic search feature requires ChromaDB for embeddings
- **Project with captions**: RAG works best when you have existing captions to learn from

## Installation

ChromaDB is optional and only needed if you want to use semantic search. If not installed, all features work normally, just without RAG capability.

To use RAG, ensure ChromaDB is installed:

```bash
pip install chromadb
```

## Getting Started

### 1. Check if RAG is Available

Navigate to **Settings**. If RAG is enabled, you'll see a "Semantic Search (RAG)" section with an "Available" badge.

### 2. Rebuild Embeddings for Your Project

1. Open a project
2. Go to **Settings**
3. In the "Semantic Search (RAG)" section, click **Rebuild Embeddings**
4. Wait for the indexing to complete (shows caption count)

This scans all active captions in your project and creates semantic embeddings from them.

### 3. Use RAG During Generation

When you generate captions with a preset:

- If RAG is enabled and embeddings exist for the project
- The system retrieves up to 2 similar captions from your dataset
- Those examples are added to the system prompt as "few-shot examples"
- The AI uses them for reference while generating the caption

## Configuration

### Rebuild Embeddings

**When**: After adding or significantly changing captions
**How**: Settings → Semantic Search (RAG) → Rebuild Embeddings
**Time**: A few seconds for typical projects (under 10,000 captions)

### Few-Shot Examples

The system automatically includes up to 2 most similar captions from your existing dataset in the prompt when RAG is enabled.

Example prompt injection:

```
[... base system prompt ...]

Example similar captions from this dataset:
  1. A dog running across a grassy field
  2. A black dog playing with a toy
```

## Performance Considerations

- **First rebuild**: Downloads embedding model (⚠️ ~80MB one-time download)
- **Subsequent rebuilds**: Fast (seconds for most projects)
- **Generation overhead**: Minimal (~100ms for semantic search per image)
- **Storage**: Embeddings stored at `.describe_it/chroma/` directory

## Graceful Degradation

If ChromaDB is not installed or becomes unavailable:

- ✅ All features continue to work normally
- ❌ RAG features silently disabled
- No errors or warnings
- Captions generated without semantic examples

## How RAG Improves Captions

### Without RAG

```
AI prompt: "Caption this image"
Result: Generic, variable quality, inconsistent style
```

### With RAG

```
AI prompt: "Caption this image

Example similar captions from this dataset:
  1. A golden retriever running in a park
  2. A dog jumping over a fence"
  
Result: Consistent style, uses dataset terminology, higher quality
```

## Troubleshooting

### "Semantic Search unavailable" message

**Problem**: ChromaDB not installed

**Solution**: 
```bash
pip install chromadb
```
Then restart the app and rebuild embeddings.

### Slow rebuild process

**Problem**: Large project or first-time embedding model download

**Expected**: First rebuild downloads ~80MB embedding model
**Solution**: Wait for initial download, subsequent rebuilds are faster

### "Rebuild Embeddings" button disabled

**Problem**: No project is open

**Solution**: Open a project first

### Embeddings seem outdated

**Problem**: Captions were changed but embeddings not rebuilt

**Solution**: Click "Rebuild Embeddings" after making caption changes

## Technical Details

### Storage

- **Embeddings location**: `.describe_it/chroma/`
- **Per-project collections**: One collection per project
- **Format**: ChromaDB PersistentClient storage (self-contained, portable)

### Collections

Projects are identified by their path stem:

```
project_name.db → captions_project_name
/path/to/my_dataset.db → captions_my_dataset
```

### Similarity Metric

- **Distance**: Cosine similarity via ONNX embeddings
- **Retrieval**: Top 2 most similar captions (configurable 1-10)
- **Score range**: 0 (no similarity) to 1 (identical)

## Advanced: Embedding Management

### View Embedding Status

1. Open project
2. Settings → Semantic Search (RAG)
3. Status shows: `"Indexed N captions"`

### Clear Embeddings

Project embeddings are automatically cleared when:
- Project is deleted
- Embeddings are manually rebuilt

### Backup Embeddings

To backup your embeddings:

```bash
cp -r ~/.describe_it/chroma /path/to/backup/
```

To restore:

```bash
cp -r /path/to/backup/chroma ~/.describe_it/
```

## Best Practices

1. **Rebuild after major changes**: Add/delete/edit multiple captions → rebuild
2. **Use consistent terminology**: RAG learns from your caption style
3. **Include examples**: RAG works best with 50+ existing captions
4. **Test the output**: Review generated captions for quality

## FAQ

**Q: Does RAG require internet?**
A: No, everything is local. Embeddings are computed and stored locally.

**Q: Can I disable RAG?**
A: Yes, simply don't rebuild embeddings. The feature works but is inactive without embeddings.

**Q: How many captions should I have?**
A: RAG works with any number, but 50+ captions give better few-shot examples.

**Q: Is this reversible?**
A: Yes. RAG is purely additive - disable it by not rebuilding, or uninstall ChromaDB.

**Q: Will this affect my existing captions?**
A: No, RAG is read-only. It never modifies captions.

## Next Steps

- ✅ Phase 7 complete: ChromaDB/RAG integration
- 🔜 Phase 8: Batch generation with RAG (coming)
- 🔜 Phase 9: Custom embedding models (coming)
