try:
    from weasyprint import HTML, CSS
    print("WeasyPrint imported successfully")
except ImportError as e:
    print(f"ImportError: {e}")
except OSError as e:
    print(f"OSError: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
