"""Generate a professional PDF explaining RevuAgent performance evaluation."""
from __future__ import annotations

from pathlib import Path

from fpdf import FPDF


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evaluation_performances.pdf"


class EvalPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(18, 53, 91)
        self.cell(0, 8, _t("RevuAgent — Évaluation des performances"), align="L")
        self.set_draw_color(6, 122, 99)
        self.set_line_width(0.4)
        y = self.get_y() + 2
        self.line(18, y, 192, y)
        self.ln(8)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            8,
            _t(f"Page {self.page_no()}/{{nb}}  |  docs/evaluation_performances.pdf"),
            align="C",
        )


def _t(s: str) -> str:
    return s.encode("latin-1", "replace").decode("latin-1")


def h1(pdf: EvalPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(18, 53, 91)
    pdf.multi_cell(pdf.epw, 9, _t(text))
    pdf.ln(2)


def h2(pdf: EvalPDF, text: str) -> None:
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(6, 122, 99)
    pdf.multi_cell(pdf.epw, 7, _t(text))
    pdf.ln(1)


def h3(pdf: EvalPDF, text: str) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(228, 87, 46)
    pdf.multi_cell(pdf.epw, 6, _t(text))
    pdf.ln(0.5)


def body(pdf: EvalPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 34, 40)
    pdf.multi_cell(pdf.epw, 5.4, _t(text))
    pdf.ln(1)


def bullet(pdf: EvalPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 34, 40)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 5.2, _t("- " + text))


def mono(pdf: EvalPDF, text: str) -> None:
    pdf.set_fill_color(245, 247, 250)
    pdf.set_font("Courier", "", 8.5)
    pdf.set_text_color(40, 44, 52)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 4.6, _t(text), fill=True)
    pdf.ln(2)


def kpi_row(pdf: EvalPDF, label: str, formula: str) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(18, 53, 91)
    pdf.cell(55, 6, _t(label), border=0)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 55, 65)
    pdf.multi_cell(pdf.epw - 55, 6, _t(formula))


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = EvalPDF(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 22, 18)
    pdf.add_page()

    h1(pdf, "Évaluation des performances")
    body(
        pdf,
        "Ce document détaille le cadre d'évaluation mis en place dans RevuAgent "
        "(pipeline agentique de revue systématique aligné PRISMA 2020). "
        "L'objectif n'est pas de prétendre à une méta-analyse statistique, "
        "mais de mesurer la qualité opérationnelle du pipeline : complétude, "
        "transparence, cohérence inter-agents et gain de temps.",
    )

    h2(pdf, "1. Objectifs de l'évaluation")
    bullet(pdf, "Vérifier que chaque étude incluse est traitée jusqu'au bout (extraction, RoB, synthèse).")
    bullet(pdf, "Quantifier la transparence des décisions (rationales explicites).")
    bullet(pdf, "Détecter les incohérences entre agents via le Critic / QA.")
    bullet(pdf, "Documenter le gain de temps par rapport à un workflow manuel équivalent.")

    h2(pdf, "2. Artefacts sources")
    body(
        pdf,
        "Après un run Partie 2, deux fichiers JSON constituent la base de l'évaluation :",
    )
    bullet(pdf, "outputs/<topic>/part2/evaluation.json — métriques agrégées du pipeline")
    bullet(pdf, "outputs/<topic>/part2/critic_report.json — verdict QA, score et issues")
    body(
        pdf,
        "Ces artefacts sont produits automatiquement par agents/report_agent.py "
        "(build_evaluation) et agents/critic_agent.py.",
    )

    h2(pdf, "3. Dimensions évaluées")

    h3(pdf, "3.1 Complétude (completeness)")
    body(
        pdf,
        "Mesure la couverture du corpus à chaque étape aval du workflow Partie 2.",
    )
    kpi_row(pdf, "screened", "nombre d'articles évalués en full-text")
    kpi_row(pdf, "included", "articles avec décision full-text = include")
    kpi_row(pdf, "extracted", "lignes de la evidence table")
    kpi_row(pdf, "appraised", "études avec Risk of Bias")
    kpi_row(pdf, "extraction_coverage", "extracted / max(included, 1)")
    body(
        pdf,
        "Interprétation : un pipeline sain vise extraction_coverage proche de 1.0 "
        "(chaque étude incluse a une extraction). Un écart signale une perte "
        "d'information entre screening et extraction.",
    )

    h3(pdf, "3.2 Transparence (transparency)")
    body(
        pdf,
        "Évalue la justifiabilité des décisions automatiques et le niveau de validation humaine.",
    )
    kpi_row(pdf, "decisions_with_rationale", "décisions full-text avec champ fulltext_reason non vide")
    kpi_row(pdf, "rationale_rate", "decisions_with_rationale / screened")
    kpi_row(pdf, "human_final_decisions", "décisions marquées comme finales (HITL)")
    kpi_row(pdf, "critic_verdict / score", "recopie du verdict QA (pass / pass_with_warnings / needs_revision)")
    body(
        pdf,
        "Interprétation : un rationale_rate élevé (proche de 1) facilite l'audit et la soutenance. "
        "L'absence de décisions humaines finales déclenche un avertissement critic : "
        "les includes/excludes restent préliminaires.",
    )

    h3(pdf, "3.3 Cohérence (consistency)")
    body(
        pdf,
        "Le Critic Agent croise les sorties des agents pour détecter les incohérences structurelles. "
        "Exemples de contrôles implémentés :",
    )
    bullet(pdf, "Nombre d'includes vs nombre d'extractions (extraction_count_mismatch)")
    bullet(pdf, "Nombre RoB vs extractions (rob_count_mismatch)")
    bullet(pdf, "Synthèse vide alors que des études sont incluses (empty_synthesis)")
    bullet(pdf, "Citations manquantes malgré une evidence table (missing_citations)")
    bullet(pdf, "Absence de décisions humaines finales / textes full-text manquants (warnings)")
    body(
        pdf,
        "Score de qualité (0-100) : départ à 100 ; -15 par issue high ; -8 par issue medium ; "
        "-3 par warning. Verdict : pass (>=80 sans issue high), pass_with_warnings (>=60), "
        "sinon needs_revision.",
    )

    h3(pdf, "3.4 Gain de temps (time savings)")
    body(
        pdf,
        "Le champ time_savings_note rappelle que le gain dépend de la taille du corpus. "
        "Pour la démonstration, comparer le wall-clock du pipeline (Partie 1 + Partie 2) "
        "à une estimation manuelle : screening titre/résumé, lecture full-text, "
        "remplissage d'une evidence table et checklist RoB sur le même jeu d'articles.",
    )
    bullet(pdf, "Mesure recommandée : chronométrer un run end-to-end sur le topic de démo.")
    bullet(pdf, "Estimation manuelle : N articles x (temps moyen screening + extraction + RoB).")
    bullet(pdf, "Reporter le ratio (temps manuel estimé / temps pipeline) dans le rapport d'équipe.")

    pdf.add_page()
    h2(pdf, "4. Exemple de structure evaluation.json")
    mono(
        pdf,
        '{\n'
        '  "completeness": {\n'
        '    "screened": 12,\n'
        '    "included": 8,\n'
        '    "extracted": 8,\n'
        '    "appraised": 8,\n'
        '    "extraction_coverage": 1.0\n'
        '  },\n'
        '  "transparency": {\n'
        '    "decisions_with_rationale": 12,\n'
        '    "rationale_rate": 1.0,\n'
        '    "human_final_decisions": 12,\n'
        '    "critic_verdict": "pass",\n'
        '    "critic_score": 94\n'
        '  },\n'
        '  "consistency": {\n'
        '    "critic_issues": [],\n'
        '    "inter_agent_checks": {}\n'
        '  },\n'
        '  "synthesis_method": "rag_narrative",\n'
        '  "time_savings_note": "..."\n'
        '}',
    )

    h2(pdf, "5. Comment lire les résultats (procédure)")
    body(pdf, "Sous PowerShell, après un run Partie 2 :")
    mono(
        pdf,
        "Get-Content outputs/<topic>/part2/evaluation.json\n"
        "Get-Content outputs/<topic>/part2/critic_report.json",
    )
    body(pdf, "Checklist de lecture rapide pour la soutenance :")
    bullet(pdf, "extraction_coverage == 1.0 ?")
    bullet(pdf, "rationale_rate élevé (>= 0.9 recommandé) ?")
    bullet(pdf, "human_final_decisions > 0 (validation HITL) ?")
    bullet(pdf, "critic_verdict = pass ou pass_with_warnings ?")
    bullet(pdf, "issues[] vide ou expliquées dans le rapport d'équipe ?")

    h2(pdf, "6. Limites méthodologiques")
    bullet(
        pdf,
        "Ces métriques évaluent le pipeline, pas la validité scientifique absolue de la revue.",
    )
    bullet(
        pdf,
        "Sans gold standard humain annoté, précision/rappel du screener ne sont pas calculés "
        "automatiquement ; ils peuvent être ajoutés manuellement si l'équipe construit un set de référence.",
    )
    bullet(
        pdf,
        "Le score critic est heuristique (règles) ou assisté LLM selon la configuration ; "
        "il complète, sans remplacer, la revue humaine.",
    )
    bullet(
        pdf,
        "Les décisions Partie 1 restent préliminaires : utiliser prisma_reconciled.json "
        "pour les compteurs finaux.",
    )

    h2(pdf, "7. Lien avec le code")
    bullet(pdf, "Construction des métriques : agents/report_agent.py -> build_evaluation()")
    bullet(pdf, "Contrôles QA : agents/critic_agent.py")
    bullet(pdf, "Export artefacts : export_part2_artefacts() écrit evaluation.json")
    bullet(pdf, "Orchestration : workflow/part2_pipeline.py")

    h2(pdf, "8. Résumé pour la soutenance")
    body(
        pdf,
        "En une phrase : RevuAgent évalue ses performances via des indicateurs de "
        "complétude, de transparence et de cohérence, avec un agent Critic qui "
        "produit un verdict et un score exploitables dans evaluation.json. "
        "Le gain de temps se démontre en comparant le wall-clock pipeline "
        "à l'effort manuel équivalent sur le même corpus.",
    )

    pdf.output(str(OUT))
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"PDF généré : {path}")
