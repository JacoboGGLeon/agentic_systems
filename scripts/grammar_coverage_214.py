"""Measure public root words actually invoked by example code, not API mentions."""
import contextlib
import inspect
from pathlib import Path
import sys

import agentic_systems as toolkit


class Coverage:
    def __init__(self):
        self.words = sorted(name for name in toolkit.__all__ if callable(getattr(toolkit, name)))
        self.codes = {}
        self.targets = {}
        for name in self.words:
            obj = getattr(toolkit, name)
            self.targets[name] = obj
            function = obj.__init__ if inspect.isclass(obj) else obj
            code = getattr(function, "__code__", None)
            if code is not None:
                self.codes.setdefault(code, []).append(name)
        self.rows = {}
        self.current = None

    def profile(self, frame, event, arg):
        if event != "call" or self.current is None or frame.f_back is None:
            return
        names = self.codes.get(frame.f_code, ())
        if not names:
            return
        caller = frame.f_back.f_code.co_filename.replace("\\", "/")
        if "/examples/common_graph/" not in caller and "/examples/context_memory_lineage/" not in caller and ".ipynb:cell-" not in caller and not caller.startswith("<ipython-input-") and "/ipykernel_" not in caller:
            return
        for name in names:
            target = self.targets[name]
            # Pydantic models share BaseModel.__init__. A user's State is not
            # a call to toolkit merely because it uses the same code.
            if inspect.isclass(target) and type(frame.f_locals.get("self")) is not target:
                continue
            self.rows[self.current].add(name)

    @contextlib.contextmanager
    def example(self, name):
        previous = self.current
        self.current = name
        self.rows.setdefault(name, set())
        before = sys.getprofile()
        sys.setprofile(self.profile)
        try:
            yield
        finally:
            sys.setprofile(before)
            self.current = previous

    def report(self):
        used = sorted(set().union(*self.rows.values()))
        return {"denominator": len(self.words), "public_root_words": self.words,
                "definition": "Constructores y funciones raíz invocados desde ejemplos/notebooks; excluye __version__, parámetros, métodos e invocaciones internas del framework. El vocabulario propio de LangGraph se informa aparte.",
                "examples": {name: {"used": sorted(words), "count": len(words), "total": len(self.words)} for name, words in self.rows.items()},
                "combined": {"used": used, "count": len(used), "total": len(self.words), "unused": sorted(set(self.words) - set(used))}}


def write_report(report, path: Path):
    lines = ["# Cobertura de gramática · " + toolkit.__version__, "", report["definition"], "",
             "| Ejemplo ejecutado | Palabras usadas / públicas |", "|---|---:|"]
    lines += [f"| {name} | {row['count']} / {row['total']} |" for name, row in report["examples"].items()]
    combined = report["combined"]
    lines += [f"| Unión de los ejemplos | **{combined['count']} / {combined['total']}** |", "",
              "Usadas: " + ", ".join(f"`{word}`" for word in combined["used"]) + ".", "",
              "No usadas: " + (", ".join(f"`{word}`" for word in combined["unused"]) if combined["unused"] else "ninguna") + ".", "",
              "La cifra mide vocabulario ejercitado, no cobertura de parámetros, ramas ni certificación de todos los proveedores. Las pruebas de regresión cubren contratos adicionales."]
    lines += ["", "Vocabulario de LangGraph empleado en el notebook ejecutado: `StateGraph`, `START`, `END`, `add_node`, `add_edge`, `add_conditional_edges`. `TypedDict` pertenece al tipado de Python. Se muestran aparte porque no son nuevas palabras del toolkit.", "", "`model_server` se ejercita como declaración; start/health/stop se prueban con simulación en la suite. No hay validación de GPU, pesos ni serving real."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
