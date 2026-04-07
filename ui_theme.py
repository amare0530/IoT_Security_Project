import streamlit as st


def inject_theme() -> None:
    """Inject a modern, high-contrast UI theme for this app."""
    st.markdown(
        """
<style>
.block-container {
    max-width: 1200px;
    padding-top: 1.2rem;
    padding-bottom: 2.5rem;
}

.hero-panel {
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 14px;
    background: linear-gradient(135deg, rgba(14, 165, 233, 0.18), rgba(16, 185, 129, 0.18));
    border: 1px solid rgba(125, 211, 252, 0.25);
}

.hero-title {
    margin: 0;
    font-size: 1.65rem;
    font-weight: 800;
    letter-spacing: 0.2px;
}

.hero-subtitle {
    margin-top: 6px;
    margin-bottom: 0;
    opacity: 0.9;
}

.status-card {
    border-radius: 12px;
    padding: 12px 14px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    margin-bottom: 8px;
    background: rgba(15, 23, 42, 0.24);
}

.status-card.ok {
    border-color: rgba(16, 185, 129, 0.5);
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.18), rgba(5, 150, 105, 0.16));
}

.status-card.warn {
    border-color: rgba(244, 114, 182, 0.45);
    background: linear-gradient(135deg, rgba(244, 63, 94, 0.18), rgba(249, 115, 22, 0.12));
}

.status-label {
    font-size: 0.85rem;
    opacity: 0.85;
}

.status-value {
    margin-top: 4px;
    font-size: 1.02rem;
    font-weight: 700;
}

.status-detail {
    margin-top: 2px;
    font-size: 0.82rem;
    opacity: 0.85;
}

.section-divider {
    margin-top: 12px;
    margin-bottom: 6px;
}

@media (max-width: 900px) {
    .hero-title {
        font-size: 1.35rem;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(label: str, value: str, is_ok: bool, detail: str = "") -> str:
    state_class = "ok" if is_ok else "warn"
    detail_html = f"<div class='status-detail'>{detail}</div>" if detail else ""
    return (
        f"<div class='status-card {state_class}'>"
        f"<div class='status-label'>{label}</div>"
        f"<div class='status-value'>{value}</div>"
        f"{detail_html}"
        f"</div>"
    )

