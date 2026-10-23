"""Reconcile teaching cards with measured results, preserving historical evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "examples/catalog.json"
DETAILS = {
    "agentic_systems_creator": ("Generar un proyecto", "Crear una aplicación con el scaffolder instalado.", "Destino nuevo → CLI → fuente, notebook y tests; generar no acredita su ejecución."),
    "research_synthesis": ("Separar afirmaciones y fuentes", "Distinguir afirmaciones con una referencia declarada de las que no la tienen.", "Dos afirmaciones y una fuente → Tool de clasificación → supported y unverified. No comprueba el contenido de la fuente."),
    "decision_intelligence": ("Comparar opciones", "Aplicar una regla de puntuación explícita.", "Calidad y coste de A/B → quality − cost → B, con puntuación 5."),
    "incident_response": ("Clasificar incidentes", "Convertir eventos en una decisión reproducible.", "Tres eventos, dos errores → regla de severidad → high e investigación."),
    "code_review": ("Inspeccionar código", "Revisar sintaxis y anotaciones de retorno con AST.", "Código Python → parseo sin ejecutarlo → función sin anotación. No es una revisión semántica completa."),
    "data_quality": ("Perfilar datos", "Detectar duplicados y valores ausentes.", "Dos registros → conteos deterministas → un ID duplicado y un importe ausente."),
    "prompt_security": ("Detectar señales en un prompt", "Marcar instrucciones sospechosas mediante reglas visibles.", "Texto → coincidencias léxicas → flags y revisión requerida. No constituye una defensa completa."),
    "meeting_action_center": ("Estructurar tareas", "Convertir notas de formato conocido en tareas.", "Responsable | tarea | fecha → Tool de parseo → lista de acciones."),
    "quantitative_analysis": ("Calcular margen", "Sumar importes con Decimal.", "Ingresos y costes → cálculo exacto → beneficio 50.25."),
    "customer_support": ("Enrutar un ticket", "Asignar un equipo mediante una regla explícita.", "Solicitud con refund → clasificación → billing."),
    "semantic_calculation": ("Calcular una factura", "Separar cálculo verificable de presentación.", "Tres unidades de 100 → subtotal e impuesto del 16% → total 348."),
    "text_analysis": ("Contar texto", "Usar un Tool para análisis básico reproducible.", "Tres palabras → conteos → dos palabras únicas y dos menciones de evidence."),
    "scope_clarification": ("Respetar el alcance", "Rechazar una operación no declarada.", "transfer_money → consulta de capacidades → accepted=False y operaciones disponibles."),
    "evidence_grounded_poem": ("Evaluar versos guardados", "Comprobar formato y una cifra en candidatos suministrados.", "Dos textos guardados → Eval → uno aceptado y otro rechazado; sin generación ni juez semántico."),
    "controlled_failure": ("Conservar un fallo", "Inspeccionar errores, eventos y linaje de una operación fallida.", "Producto A17 → Tool lanza LookupError → RunResult fallido con evidencia e invariantes válidas."),
    "strands_protocol_graph": ("Conectar MCP y A2A", "Usar servicios locales reales desde Strands.", "Valor conocido → MCP Streamable HTTP y agente A2A → evidencia remota; modelos deterministas y cero inferencia."),
    "bounded_conversation": ("Acotar una conversación", "Mantener una ventana de contexto explícita.", "Cuatro mensajes → últimas tres entradas, longitud acotada → historia conservada."),
    "two_phase_poem": ("Calcular antes de presentar", "Conservar evidencia de un Tool al formatear una respuesta.", "3 × 116 → Tool exact_total → tres versos de una plantilla con total 348; sin generación de lenguaje."),
    "compact_evaluation": ("Evaluar y resumir evidencia", "Evaluar una ejecución guardada y consultar su traza.", "Suma 2 + 3 → guardar RunResult → Eval, trace y lineage sin repetir el candidato."),
    "claim_review": ("Revisar referencias y causalidad", "Aplicar comprobaciones explícitas sobre afirmaciones estructuradas.", "Fuente ausente y causalidad sin evidencia declarada → dos hallazgos → accepted=False."),
    "typed_claim_review": ("Validar una afirmación tipada", "Rechazar datos que incumplen el esquema de entrada.", "Una entrada válida y otra con texto numérico → Tool con esquema estricto → éxito y fallo conservados."),
    "judge_calibration": ("Comprobar un juez optimista", "Combinar expectativas exactas y un juez fixture.", "Respuestas VALID y WRONG → juez que siempre aprueba + expectativas → [True, False]; no es calibración empírica de un modelo."),
    "long_environment": ("Recorrer un episodio", "Acumular memoria sin contaminar la siguiente ejecución.", "Treinta movimientos de +1 → Environment con memoria → balance 30 en dos episodios independientes."),
    "saved_execution_eval": ("Evaluar sin repetir", "Restaurar RunResult y evaluar evidencia guardada.", "Suma 2 + 3 → serialización → Eval acepta total 5 sin volver a ejecutar el cálculo."),
    "api_contract_lab": ("Comparar run y compile", "Comprobar que preparar una unidad conserva su ejecución.", "value=3 → run directo y compile().run → mismo resultado; firmas públicas disponibles."),
    "provider_framework_conformance": ("Ejecutar cuatro frameworks", "Usar los cuatro SDKs con Python determinista.", "value=3 → Tool echo en native, LangGraph, OpenAI Agents y Strands → misma evidencia; la matriz live se documenta aparte."),
    "vllm_colab": ("Preparar vLLM/Colab", "Inspeccionar la configuración antes de conectarse a una GPU.", "Variables del entorno → runtime y Agent → contrato inspeccionable; GPU y endpoint pendientes."),
    "aws_iam": ("Preparar AWS IAM", "Declarar Bedrock sin una API key embebida.", "Modelo y región → runtime → configuración; el proceso de destino debe usar su rol IAM sin bearer token. Autenticación pendiente."),
    "ada_iam": ("Preparar ADA IAM", "Preparar el mismo contrato para un workload empresarial.", "Modelo y región → runtime → configuración; rol, red y dependencias de ADA requieren prueba en ese entorno. Sin extra [ada]."),
    "refund_resolution": ("Resolver un reembolso", "Aplicar una política de negocio pequeña y visible.", "280 MXN, cuenta de 90 días → regla declarada → approved; datos sintéticos."),
    "fixed_judge_pilot": ("Bloquear un falso positivo", "Impedir que un juez fixture apruebe una respuesta incorrecta.", "WRONG → expectativa VALID y juez optimista → caso rechazado, conservando ambos resultados."),
    "unambiguous_lm_gate": ("Exigir una respuesta literal", "Distinguir coincidencia exacta de parecido textual.", "VALID, VALID., invalid y vacío → Eval → solo VALID aceptado; respuestas guardadas, sin modelo."),
    "unified_grammar": ("Agent y System: seis flujos", "Aprender secuencia, paralelo y decisiones con la misma interfaz.", "value=3 → seis declaraciones en native y LangGraph, Environment y Eval → resultados y linaje verificables."),
    "retired_accountability_otc": ("Asignar responsables a evidencia", "Mostrar un reemplazo público y sintético del experimento retirado.", "Dos afirmaciones → comprobar owner/evidence → C2 sin responsable ni respaldo. El código privado original no se recuperó."),
}


def ref(label, path):
    return {"label": label, "target": path}


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    # Keep one teaching entry for framework conformance; both implementations
    # remain linked so existing source links continue to work.
    duplicate = next((e for e in catalog["entries"] if e["id"] == "provider_framework_conformance_213"), None)
    if duplicate:
        catalog["entries"].remove(duplicate)
        original = next(e for e in catalog["entries"] if e["id"] == "provider_framework_conformance")
        original["related_sources"] = duplicate["sources"]
    for entry in catalog["entries"]:
        slug = entry["id"]
        if slug in DETAILS:
            directory = ROOT / "examples" / entry["group"] / slug
            evidence_path = directory / "evidence/current.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            assert evidence["example_passed"] and evidence["inference_requests"] == 0
            assert evidence["source_sha256"] == hashlib.sha256((directory / "example.py").read_bytes()).hexdigest()
            entry["title"], entry["purpose"], entry["flow"] = DETAILS[slug]
            entry["entrypoint"] = f"examples.{entry['group']}.{slug}.example:run"
            configuration = slug in {"vllm_colab", "aws_iam", "ada_iam"}
            entry["readiness"] = "target environment pending" if configuration else "offline execution passed"
            entry["validation"] = {"status": "configuration-only" if configuration else "offline-only",
                "scope": ("Configuración construida e inspeccionada. El entorno de destino no se ejecutó." if configuration else
                          "Adaptación 2.1.3 ejecutada offline. Las aserciones comprueban el alcance descrito; cero inferencia. Los fallos intencionales se verifican como resultados esperados."),
                "evidence": [ref("Ejecución actual", evidence_path.relative_to(ROOT).as_posix())]}
            entry["next_action"] = "Ejecutar en el entorno de destino." if configuration else "Importar run y consultar su resultado y evidencia."
        elif slug != "api_213_tutorials":
            source = next((r["target"] for r in entry["sources"] if r["target"].endswith("example.py")), None)
            if slug == "order_fulfillment_213":
                source = "examples/order_fulfillment/example.py"
            if source:
                entry["entrypoint"] = source.removesuffix(".py").replace("/", ".") + ":run"
    extras = [
        {"id": "framework_interop", "title": "Cuatro frameworks juntos", "group": "applications",
         "purpose": "Coordinar actores de cuatro SDKs y conservar la evidencia de cada Tool.",
         "flow": "42 y trail vacío → native, LangGraph, OpenAI Agents y Strands → 46 y cuatro identidades. También se probó la asignación mixta Python/OpenAI/Ollama/Bedrock.",
         "entrypoint": "examples.framework_interop.example:run", "sources": [ref("Implementación", "examples/framework_interop/example.py")],
         "validation": {"status": "live-tested", "scope": "Interop Python y mixta ejecutadas. La tarea exige argumentos intactos y resultados observados de Tools; no es una certificación de cualquier workflow.",
                        "evidence": [ref("Campaña y límites", "revisions/2.1.3/framework-evidence/REPORT.md")]}},
        {"id": "studio", "title": "Studio", "group": "applications",
         "purpose": "Conversar, conservar contexto y usar una calculadora con un proveedor y framework explícitos.",
         "flow": "Conversación de tres turnos → contexto acotado, Tool y actor → texto, evidencia y RunResult. Python es un mock visible.",
         "sources": [ref("Abrir Studio", "examples/agentic_systems_studio/README.md"), ref("Aplicación", "examples/agentic_systems_studio/src/agentic_systems_studio/conversation.py")],
         "validation": {"status": "live-tested", "scope": "Backend: 16 combinaciones, tres turnos cada una. Las pruebas de widgets y sus límites se detallan en el informe; no implica cualquier consulta o entorno.",
                        "evidence": [ref("Resultados", "revisions/2.1.3/framework-evidence/REPORT.md")]}}
    ]
    for entry in extras:
        catalog["entries"] = [e for e in catalog["entries"] if e["id"] != entry["id"]]
        catalog["entries"].append({"api_version": "2.1.3", **entry})
    catalog["current_adaptations"] = {"historical_experiments": 34, "offline_executed": 34, "target_configuration_only": 3}
    catalog["reviewed_at"] = "2026-10-22"
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Reconciled {len(catalog['entries'])} entries; 34 historical adaptations verified.")


if __name__ == "__main__":
    main()
