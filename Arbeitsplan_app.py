import streamlit as st
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

# ──────────────────────────────
# Session State Initialisierung
# ──────────────────────────────

if "events" not in st.session_state:
    st.session_state.events = [
        {
            "id": "e1",
            "name": "Festival Berlin",
            "ort": "Berlin",
            "required_dates": ["2024-06-01"],
            "required_mitarbeiter": 5,
            "anzahl_staende": 3,
            "mitarbeiter_pro_stand": 2,
            "required_fuehrerscheine": {"BE": 1, "B": 2, "none": 2},
            "needs_leiter": True,
            "prioritaet": "1"
        },
        # Füge hier weitere Standard-Events hinzu, falls gewünscht
    ]

if "mitarbeiter" not in st.session_state:
    st.session_state.mitarbeiter = [
        {
            "id": "m1",
            "name": "Anna Schmidt",
            "fuehrerscheine": ["B"],
            "erfahrung_level": 2,
            "verfuegbare_termine": ["2024-06-01", "2024-06-15", "2024-07-05", "2024-07-06"]
        },
        {
            "id": "m2",
            "name": "Bob Müller",
            "fuehrerscheine": ["BE"],
            "erfahrung_level": 1,
            "verfuegbare_termine": ["2024-06-01", "2024-06-02", "2024-06-15", "2024-07-05"]
        },
        # ... deine weiteren Mitarbeiter ...
        {
            "id": "m6",
            "name": "Emma dasdsFischer",
            "fuehrerscheine": ["BE"],
            "erfahrung_level": 1,
            "verfuegbare_termine": ["2024-06-01", "2024-07-05"]
        },
    ]

events = st.session_state.events
mitarbeiter = st.session_state.mitarbeiter

# ──────────────────────────────
# Hilfsfunktionen
# ──────────────────────────────

def matches_license(fuehrerscheine: List[str], req_class: str) -> bool:
    if req_class == "none":
        return True
    if req_class == "B":
        return "B" in fuehrerscheine or "BE" in fuehrerscheine
    if req_class == "BE":
        return "BE" in fuehrerscheine
    return False


def assign_to_event(
    candidates: List[Dict],
    required_fuehrerscheine: Dict[str, int],
    effective_required: int,
    needs_leiter: bool
) -> Tuple[Optional[List[Dict]], Optional[str]]:
    if len(candidates) < effective_required:
        return None, f"Nur {len(candidates)} Kandidaten verfügbar (brauche {effective_required})"

    assigned = []
    remaining = candidates[:]
    quota = required_fuehrerscheine.copy()

    license_order = sorted(quota.keys(), key=lambda x: 0 if x == "none" else 1 if x == "B" else 2, reverse=True)

    for lic in license_order:
        needed = quota.get(lic, 0)
        if needed <= 0: continue
        suitable = [m for m in remaining if matches_license(m["fuehrerscheine"], lic)]
        suitable.sort(key=lambda m: -m["erfahrung_level"])
        for _ in range(min(needed, len(suitable))):
            sel = suitable.pop(0)
            assigned.append(sel)
            remaining.remove(sel)

    still_needed = effective_required - len(assigned)
    if still_needed > 0:
        remaining.sort(key=lambda m: -m["erfahrung_level"])
        assigned += remaining[:still_needed]

    if len(assigned) < effective_required:
        return None, f"Nur {len(assigned)} von {effective_required} zugewiesen"

    if needs_leiter and max((m["erfahrung_level"] for m in assigned), default=0) < 2:
        leiter_avail = [m for m in candidates if m["erfahrung_level"] >= 2 and m not in assigned]
        if leiter_avail:
            assigned.sort(key=lambda m: m["erfahrung_level"])
            assigned[0] = leiter_avail[0]
        else:
            return None, "Kein Eventleiter verfügbar"

    return assigned, None

# ──────────────────────────────
# Streamlit Oberfläche
# ──────────────────────────────

st.set_page_config(page_title="Arbeitsplan Tool", layout="wide")
st.title("🚀 Arbeitsplan erstellen")

# ──────────────────────────────
# Navigation mit Tabs
# ──────────────────────────────

tab1, tab2, tab3 = st.tabs(["📅 Planung", "➕ Events verwalten", "👤 Mitarbeiter verwalten"])

# ────────────────────────────────────────────────
# TAB 1: Planung
# ────────────────────────────────────────────────
with tab1:
    st.subheader("Bestehende Events planen")

    if st.button("Plan jetzt berechnen", type="primary", use_container_width=True):
        with st.spinner("Mitarbeiter werden zugewiesen …"):
            worker_used_dates = {m["id"]: set() for m in mitarbeiter}
            plan = {}
            sorted_events = sorted(events, key=lambda e: e["required_dates"][0] if e["required_dates"] else "")

            for event in sorted_events:
                candidates = [
                    m for m in mitarbeiter
                    if all(d not in worker_used_dates[m["id"]] for d in event["required_dates"])
                ]
                effective_required = max(
                    event["required_mitarbeiter"],
                    event["anzahl_staende"] * event["mitarbeiter_pro_stand"]
                )

                assigned, error = assign_to_event(
                    candidates,
                    event["required_fuehrerscheine"],
                    effective_required,
                    event["needs_leiter"]
                )

                if error:
                    plan[event["id"]] = {"status": "FEHLER", "grund": error, "mitarbeiter": []}
                else:
                    plan[event["id"]] = {
                        "status": "OK",
                        "mitarbeiter": [m["name"] for m in assigned],
                        "anzahl": len(assigned)
                    }
                    for m in assigned:
                        for d in event["required_dates"]:
                            worker_used_dates[m["id"]].add(d)

            st.subheader("🎉 Fertiger Arbeitsplan")
            for ev in sorted_events:
                p = plan.get(ev["id"], {})
                with st.expander(f"{ev['name']} – {ev['required_dates']} ({ev['ort']})"):
                    if p.get("status") == "OK":
                        st.success(f"{p['anzahl']} Personen: {', '.join(p['mitarbeiter'])}")
                    else:
                        st.error(f"FEHLER: {p.get('grund', 'Unbekannt')}")

# ────────────────────────────────────────────────
# TAB 2: Events verwalten
# ────────────────────────────────────────────────
with tab2:
    st.subheader("➕ Neues Event anlegen")

    with st.form(key="neues_event_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            event_name = st.text_input("Eventname", placeholder="z. B. Festival Berlin")
            event_ort = st.text_input("Eventort", placeholder="z. B. Berlin")
        with col2:
            event_datum = st.date_input("Eventdatum (Haupttag)", value=None)
            hotel_voranreise = st.checkbox("Hotel vor Anreise", help="Mitarbeiter müssen bereits am Vortag anreisen")
            hotel_nachreise = st.checkbox("Hotel nach Abreise", help="Mitarbeiter können erst am Folgetag abreisen")

        st.markdown("---")

        col3, col4, col5 = st.columns(3)
        with col3:
            anzahl_staende = st.number_input("Anzahl Verkaufsstände", min_value=0, max_value=20, value=1, step=1)
        with col4:
            mitarbeiter_gesamt = st.number_input("Mindestanzahl Mitarbeiter insgesamt", min_value=0, max_value=50, value=4, step=1)
        with col5:
            prioritaet = st.selectbox(
                "Priorität",
                options=["1 – sehr wichtig", "2 – mittelwichtig", "3 – eher unwichtig", "4 – optional / behalten vor"],
                index=1
            )

        st.markdown("**Führerschein-Anforderungen**")
        col_fs1, col_fs2, col_fs3 = st.columns(3)
        with col_fs1:
            fs_b = st.number_input("× Klasse B", min_value=0, max_value=10, value=0, step=1)
        with col_fs2:
            fs_be = st.number_input("× Klasse BE", min_value=0, max_value=10, value=0, step=1)
        with col_fs3:
            fs_none = st.number_input("× ohne Führerschein", min_value=0, max_value=20, value=0, step=1)

        submitted = st.form_submit_button("Event speichern", type="primary", use_container_width=True)

        if submitted:
            if not event_name.strip():
                st.error("Eventname erforderlich")
            elif event_datum is None:
                st.error("Datum erforderlich")
            elif anzahl_staende == 0:
                st.error("Mindestens 1 Stand erforderlich")
            else:
                datum_str = event_datum.strftime("%Y-%m-%d")
                required_dates = [datum_str]

                if hotel_voranreise:
                    required_dates.insert(0, (event_datum - timedelta(days=1)).strftime("%Y-%m-%d"))
                if hotel_nachreise:
                    required_dates.append((event_datum + timedelta(days=1)).strftime("%Y-%m-%d"))

                neues_event = {
                    "id": f"e{len(events)+1}",
                    "name": event_name.strip(),
                    "ort": event_ort.strip() or "—",
                    "required_dates": required_dates,
                    "required_mitarbeiter": mitarbeiter_gesamt,
                    "anzahl_staende": anzahl_staende,
                    "mitarbeiter_pro_stand": 2,
                    "required_fuehrerscheine": {"BE": fs_be, "B": fs_b, "none": fs_none},
                    "needs_leiter": False,
                    "prioritaet": prioritaet[0]
                }

                events.append(neues_event)
                st.success(f"Event '{event_name}' wurde hinzugefügt!")
                st.balloons()

    # Liste aller Events + Bearbeiten / Löschen
    st.subheader("📋 Alle Events")

    if not events:
        st.info("Noch keine Events vorhanden. Füge oben eines hinzu.")
    else:
        for idx, ev in enumerate(events):
            with st.expander(f"{ev['name']} – {ev['required_dates']} ({ev['ort']}) | Priorität {ev['prioritaet']}"):
                col_a, col_b = st.columns([6, 1])
                with col_a:
                    edit_name = st.text_input("Name", value=ev["name"], key=f"edit_name_{idx}")
                    edit_ort = st.text_input("Ort", value=ev["ort"], key=f"edit_ort_{idx}")
                    edit_dates = st.text_input("Termine (kommagetrennt)", value=", ".join(ev["required_dates"]), key=f"edit_dates_{idx}")
                    edit_staende = st.number_input("Verkaufsstände", value=ev["anzahl_staende"], key=f"edit_staende_{idx}")
                    edit_mw = st.number_input("Mind. Mitarbeiter", value=ev["required_mitarbeiter"], key=f"edit_mw_{idx}")

                    edit_fs_b = st.number_input("× B", value=ev["required_fuehrerscheine"].get("B", 0), key=f"edit_fsb_{idx}")
                    edit_fs_be = st.number_input("× BE", value=ev["required_fuehrerscheine"].get("BE", 0), key=f"edit_fsbe_{idx}")
                    edit_fs_none = st.number_input("× none", value=ev["required_fuehrerscheine"].get("none", 0), key=f"edit_fsnone_{idx}")

                    if st.button("Änderungen speichern", key=f"save_{idx}"):
                        try:
                            ev["name"] = edit_name.strip()
                            ev["ort"] = edit_ort.strip()
                            ev["required_dates"] = [d.strip() for d in edit_dates.split(",")]
                            ev["anzahl_staende"] = edit_staende
                            ev["required_mitarbeiter"] = edit_mw
                            ev["required_fuehrerscheine"] = {"B": edit_fs_b, "BE": edit_fs_be, "none": edit_fs_none}
                            st.success("Event aktualisiert!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler beim Speichern: {e}")

                with col_b:
                    if st.button("🗑️ Löschen", key=f"delete_{idx}", type="primary"):
                        del events[idx]
                        st.success("Event gelöscht!")
                        st.rerun()

# ────────────────────────────────────────────────
# TAB 3: Mitarbeiter verwalten
# ────────────────────────────────────────────────
with tab3:
    st.subheader("👤 Mitarbeiter verwalten")

    # ─── Neuen Mitarbeiter anlegen ──────────────────────────────────
    with st.expander("➕ Neuen Mitarbeiter anlegen", expanded=False):
        with st.form(key="neuer_mitarbeiter", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                vorname = st.text_input("Vorname")
                nachname = st.text_input("Nachname")
                name = f"{vorname.strip()} {nachname.strip()}".strip()

            with col2:
                erfahrung = st.selectbox(
                    "Erfahrung",
                    options=[
                        "Eventleiter (kann leiten + unerfahrene mitnehmen)",
                        "Kann alleine ein Event leiten",
                        "Nur als Hilfskraft (keine Verantwortung)"
                    ],
                    index=1
                )
                erf_level_map = {
                    "Eventleiter ...": 3,
                    "Kann alleine ...": 2,
                    "Nur als Hilfskraft ...": 1
                }
                erfahrung_level = erf_level_map[erfahrung]

            fuehrerschein = st.multiselect(
                "Führerscheinklassen",
                options=["Klasse B", "Klasse BE"],
                default=[]
            )

            submitted_m = st.form_submit_button("Mitarbeiter speichern", type="primary")

            if submitted_m:
                if not name:
                    st.error("Vor- und Nachname erforderlich")
                else:
                    neuer_m = {
                        "id": f"m{len(mitarbeiter)+1}",
                        "name": name,
                        "fuehrerscheine": ["B" if "Klasse B" in fuehrerschein else "BE" if "Klasse BE" in fuehrerschein else []],
                        "erfahrung_level": erfahrung_level,
                        "verfuegbare_termine": []
                    }
                    mitarbeiter.append(neuer_m)
                    st.success(f"Mitarbeiter {name} angelegt!")
                    st.rerun()

    # ─── Liste aller Mitarbeiter + Bearbeiten / Löschen ─────────────
    st.subheader("Aktuelle Mitarbeiter")

    if not mitarbeiter:
        st.info("Noch keine Mitarbeiter vorhanden.")
    else:
        data = []
        for m in mitarbeiter:
            data.append({
                "ID": m["id"],
                "Name": m["name"],
                "Erfahrung": {3: "Eventleiter", 2: "Kann allein", 1: "Hilfskraft"}.get(m["erfahrung_level"], "?"),
                "Führerscheine": ", ".join(m["fuehrerscheine"]) or "—",
                "Verfügbare Tage": len(m["verfuegbare_termine"])
            })
        st.dataframe(data, use_container_width=True)

        for idx, m in enumerate(mitarbeiter):
            with st.expander(f"{m['name']} ({m['id']})"):
                col_del, col_edit = st.columns([1, 5])

                with col_del:
                    if st.button("🗑️ Löschen", key=f"del_m_{idx}", type="primary"):
                        del mitarbeiter[idx]
                        st.success("Mitarbeiter gelöscht")
                        st.rerun()

                with col_edit:
                    edit_vorname = st.text_input("Vorname", value=m["name"].split()[0] if " " in m["name"] else m["name"], key=f"evn_{idx}")
                    edit_nachname = st.text_input("Nachname", value=" ".join(m["name"].split()[1:]) if " " in m["name"] else "", key=f"enn_{idx}")
                    edit_erf = st.selectbox(
                        "Erfahrung",
                        options=["Eventleiter (3)", "Kann allein (2)", "Hilfskraft (1)"],
                        index=3 - m["erfahrung_level"],
                        key=f"eerf_{idx}"
                    )
                    edit_erf_level = int(edit_erf[-2])

                    edit_fs = st.multiselect(
                        "Führerscheine",
                        options=["Klasse B", "Klasse BE"],
                        default=m["fuehrerscheine"],
                        key=f"efs_{idx}"
                    )

                    if st.button("Änderungen speichern", key=f"save_m_{idx}"):
                        m["name"] = f"{edit_vorname.strip()} {edit_nachname.strip()}".strip()
                        m["erfahrung_level"] = edit_erf_level
                        m["fuehrerscheine"] = ["B" if "B" in edit_fs else "BE" if "BE" in edit_fs else []]
                        st.success("Gespeichert!")
                        st.rerun()

    # ─── Verfügbarkeit eintragen ─────────────────────────────────────
    st.subheader("Verfügbarkeit eintragen")

    if mitarbeiter:
        selected_name = st.selectbox(
            "Mitarbeiter auswählen",
            options=[m["name"] for m in mitarbeiter],
            index=0
        )

        m = next(m for m in mitarbeiter if m["name"] == selected_name)

        st.write(f"**Aktuelle verfügbare Tage für {m['name']}:**")
        if m["verfuegbare_termine"]:
            st.write(", ".join(sorted(m["verfuegbare_termine"])))
        else:
            st.info("Noch keine Tage eingetragen.")

        neue_tage = st.date_input(
            "Verfügbare Tage hinzufügen (Mehrfachauswahl möglich)",
            value=[],
            min_value=datetime(2024, 1, 1),
            max_value=datetime(2026, 12, 31),
            format="YYYY-MM-DD"
        )

        if st.button("Tage hinzufügen"):
            if isinstance(neue_tage, datetime):
                neue_tage = [neue_tage]
            neue_str = [t.strftime("%Y-%m-%d") for t in neue_tage if t]
            already = set(m["verfuegbare_termine"])
            added = [d for d in neue_str if d not in already]
            m["verfuegbare_termine"].extend(added)
            m["verfuegbare_termine"] = sorted(set(m["verfuegbare_termine"]))
            st.success(f"{len(added)} neue Tage hinzugefügt!")
            st.rerun()

        if m["verfuegbare_termine"]:
            to_delete = st.multiselect(
                "Tage entfernen",
                options=m["verfuegbare_termine"],
                default=[]
            )
            if st.button("Ausgewählte Tage löschen"):
                m["verfuegbare_termine"] = [d for d in m["verfuegbare_termine"] if d not in to_delete]
                st.success(f"{len(to_delete)} Tage entfernt")
                st.rerun()
    else:
        st.info("Erstelle zuerst einen Mitarbeiter.")
