import logging

_CONFIGURED = False


def configure_logging(verbose: bool = False) -> None:
    """Configure a single stderr handler for the whole library."""
    global _CONFIGURED
    level = logging.DEBUG if verbose else logging.INFO
    if _CONFIGURED:
        logging.getLogger("lit_graph").setLevel(level)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    root = logging.getLogger("lit_graph")
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name if name.startswith("lit_graph") else f"lit_graph.{name}")
