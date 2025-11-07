import logging, os, sys

def setup_logger(log_dir: str, level: str = "INFO"):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s :: %(message)s",
                            datefmt="%Y-%m-%dT%H:%M:%SZ")
    ch = logging.StreamHandler(sys.stdout); ch.setFormatter(fmt); logger.addHandler(ch)
    fh = logging.FileHandler(os.path.join(log_dir, "app.log")); fh.setFormatter(fmt); logger.addHandler(fh)
    return logger