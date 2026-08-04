"""
state_table.py

Render a parsed state model as a markdown state transition table.

The page holds the compact transition matrix for the wait states, followed by the reasoning
behind each declared ignore and can't happen response.
"""
from pathlib import Path

DEFAULTED = ""  # A cell with no declared response at all


def model_name(sm):
    """A lifecycle is named for its class, an assigner for its relationship."""
    if sm.lifecycle:
        return sm.lifecycle
    return f"{sm.assigner_rnum} / {sm.assigner_pclass}" if sm.assigner_pclass else sm.assigner_rnum


def meta(sm, field):
    """The value of a metadata field, or None if the model doesn't supply it"""
    if not sm.metadata or field not in sm.metadata:
        return None
    return sm.metadata[field][0]


def tag_table(sm):
    """Reusable reasons are file scoped: the occurrence carrying text defines the tag."""
    return {r.tag: r.explanation
            for s in sm.states for r in list(s.ignores) + list(s.cant_happens)
            if r.tag and r.explanation}


def reason(r, tags):
    """The explanation for a response, resolving a bare tag reference to its definition"""
    return r.explanation if r.explanation else tags.get(r.tag, "")


def responses(s):
    """event -> (kind, destination, response) for everything this state declares."""
    out = {t.event: ("transition", t.to_state, None) for t in s.transitions}
    out.update({r.event: ("ignore", None, r) for r in s.ignores})
    out.update({r.event: ("can't happen", None, r) for r in s.cant_happens})
    return out


def creation_events(sm):
    """Events answered by an initial transition rather than by any state"""
    return {t.event for t in sm.initial_transitions}


def wait_states(sm):
    """The all caps convention marks a state where the instance waits for an event"""
    return [s for s in sm.states if s.state.name.isupper()]


def matrix_events(sm):
    """Every declared event that could be a column, so every event but the creation events"""
    return [e for e in sm.events if e not in creation_events(sm)]


def dead_columns(sm):
    """
    Events whose matrix column would be entirely blank, so they are dropped.

    Only a completion event qualifies. An interaction event no wait state answers is not blank,
    it is undecided in every one of them, and dropping the column would hide that.
    """
    return [e for e in matrix_events(sm)
            if e not in sm.interaction_events
            and all(e not in responses(s) for s in wait_states(sm))]


def undecided_responses(sm):
    """
    (state, event) pairs where a wait state declares no response to an interaction event.

    Such an event can arrive, so the absence of a response is an open question. A completion
    event cannot arrive at all, so its absence is systematic and not reported.
    """
    return [(s.state.name, e) for s in wait_states(sm) for e in matrix_events(sm)
            if e not in responses(s) and e in sm.interaction_events]


def orphan_events(sm):
    """Declared events that no state answers in any way"""
    answered = {e for s in sm.states for e in responses(s)}
    return [e for e in matrix_events(sm) if e not in answered]


def page(sm, source):  # noqa: C901
    """
    The complete markdown page for one state model

    :param sm: The parsed state model
    :param source: Name of the .xsm file it was parsed from, quoted in the do not edit banner
    :return: The page text with no trailing newline
    """
    tags = tag_table(sm)
    waits = wait_states(sm)
    transients = [s for s in sm.states if not s.state.name.isupper()]
    events = matrix_events(sm)

    out = [f"# {model_name(sm)}", ""]
    title, version, modified = meta(sm, "Title"), meta(sm, "Version"), meta(sm, "Modification date")
    if title:
        out += [f"*{title}" + (f" — version {version}, {modified}*" if version else "*"), ""]
    out += [f"<!-- generated from {source} - do not edit -->", ""]

    if sm.initial_transitions:
        for t in sm.initial_transitions:
            out.append(f"Instances are created into **{t.to_state}** by the `{t.event}` event.")
        out.append("")

    out += ["Rows are the wait states. A cell marked **?** is an interaction event with no declared "
            "response — it defaults to can't happen, but nobody has said why. A blank cell is a "
            "completion event that cannot be received here.", ""]
    if transients:
        names = ", ".join(f"`{s.state.name}`"
                          + (" *(deletion)*" if s.state.deletion else "") for s in transients)
        out += [f"The transient states — {names} — accept only their own completion event; "
                f"every other event can't happen.", ""]

    # ------------------------------------------------------------------ matrix
    # An event no wait state answers is structurally blank down the whole column. Those are
    # completion events consumed only by transient states, which are not rows here, so the
    # column is dropped to keep the matrix readable.
    dead = dead_columns(sm)
    columns = [e for e in events if e not in dead]
    undecided = undecided_responses(sm)

    out += ["## State transition table", ""]
    out.append("| |" + "|".join(f" {e} " for e in columns) + "|")
    out.append("|---|" + "|".join("---" for _ in columns) + "|")
    for s in waits:
        rs = responses(s)
        cells = []
        for e in columns:
            if e not in rs:
                cells.append(" ? " if e in sm.interaction_events else f" {DEFAULTED} ")
            else:
                kind, dest, _ = rs[e]
                cells.append(f" **{dest}** " if kind == "transition" else f" {kind} ")
        out.append(f"| **{s.state.name}** |" + "|".join(cells) + "|")
    out.append("")
    if dead:
        out += [f"{', '.join(f'`{e}`' for e in dead)} "
                f"{'are' if len(dead) > 1 else 'is'} answered only by a transient state, so "
                f"{'those columns are' if len(dead) > 1 else 'that column is'} omitted.", ""]
    if undecided:
        out += [f"⚠️ {len(undecided)} interaction event "
                f"{'responses have' if len(undecided) > 1 else 'response has'} not been decided:",
                ""]
        for name in [s.state.name for s in waits]:
            open_here = [e for st, e in undecided if st == name]
            if open_here:
                out.append(f"- **{name}** — {', '.join(f'`{e}`' for e in open_here)}")
        out.append("")

    # ------------------------------------------------- per state detail tables
    # Only the declared non transition responses appear here. A transition carries no
    # explanation, and a defaulted can't happen is systematic, so both would contribute
    # nothing but an empty row.
    out += ["## Non transition event responses", ""]
    for s in waits:
        declared = {r.event: (kind, r)
                    for kind, group in (("ignore", s.ignores), ("can't happen", s.cant_happens))
                    for r in group}
        out += [f"### {s.state.name}", ""]
        if not declared:
            out += ["*Every event is either a transition or a systematic can't happen.*", ""]
            continue
        out += ["| Event | Response | Explanation |", "|---|---|---|"]
        for e in events:
            if e in declared:
                kind, r = declared[e]
                out.append(f"| {e} | {kind} | {reason(r, tags)} |")
        out.append("")
    return "\n".join(out)


def write(sm, model_path, out_dir=None):
    """
    Write the markdown page for a parsed model

    :param sm: The parsed state model
    :param model_path: Path of the .xsm file it was parsed from
    :param out_dir: Where to write the page, defaulting to the model file's own directory
    :return: Path of the file written
    """
    model_path = Path(model_path)
    destination = Path(out_dir) if out_dir else model_path.parent
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{model_path.stem}.md"
    target.write_text(page(sm, model_path.name) + "\n", encoding="utf-8")
    return target
