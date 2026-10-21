"""PDF parsing in a short-lived process with POSIX CPU/address-space limits."""
import io
import json
import sys


def main():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    except (ImportError, ValueError, OSError):
        # The web process also enforces a five-second wall deadline.
        pass
    from pypdf import PdfReader
    import pypdf.filters as filters
    filters.ZLIB_MAX_OUTPUT_LENGTH = 2 * 1024 * 1024
    filters.LZW_MAX_OUTPUT_LENGTH = 2 * 1024 * 1024
    filters.RUN_LENGTH_MAX_OUTPUT_LENGTH = 2 * 1024 * 1024
    try:
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("PDF must be at most 1 MiB")
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")
        if not 1 <= len(reader.pages) <= 10:
            raise ValueError("PDF must contain 1 to 10 pages")
        pages, total = [], 0
        for page in reader.pages:
            text = page.extract_text() or ""
            total += len(text)
            if total > 50000:
                raise ValueError("Extracted text exceeds 50,000 characters")
            pages.append(text)
        if sum(len(page.strip()) for page in pages) < 30:
            raise ValueError("No usable text found. Scanned PDFs need OCR; paste text instead.")
        print(json.dumps({"pages": pages}))
    except Exception:
        print(json.dumps({"error": "PDF could not be read. Use a text PDF of at most 10 pages and 1 MiB, or paste its text."}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
