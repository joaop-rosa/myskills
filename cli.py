#!/usr/bin/env python3
"""Ponto de entrada executável da CLI de gerenciamento de skills."""

from __future__ import annotations

import sys

from skills_cli.main import main

if __name__ == "__main__":
    sys.exit(main())
