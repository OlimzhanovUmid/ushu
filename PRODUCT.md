# Product

## Register

product

## Platform

web

## Users

Four groups share the same LAN system during a wushu competition, each on a different screen and under different pressure.

Category judges (A/B/C class) are the hot path: they sit at client machines and enter live scores for the athlete currently performing, under time pressure, and must never submit the wrong value by accident. The main (staff) judge controls flow — reopening a participation, confirming and saving the final result. The organizer/registrar works before and between rounds: registering athletes with age/sex/club, running the random draw (jrebiy), and managing the tablo grid. Spectators and athletes read the projector monitor from across a hall — they never touch the system, only watch who is up, the scores as they land, and the standings.

The tool runs on a single server laptop feeding roughly ten weak client machines plus one projector over a local network. UI text is Russian.

## Product Purpose

A single system that runs an entire wushu competition end to end — participant registration, random draw, live A/B/C judging, final results, and the public projector screen — so nothing has to be exported, re-tallied, or re-entered between stages. It replaces the paper-and-clipboard workflow. Success is two things at once: a judge enters the correct score fast and without mis-taps, and the projector screen stays legible to a whole hall at a glance.

## Positioning

One screen for the whole competition: registration → draw → live judging → results → projector, with no hand-off, export, or manual tallying in between. Every screen is part of one continuous event flow, not a standalone form.

## Brand Personality

Authoritative and calm — the confidence of an official sports federation. Precise, unflashy, and trustworthy under competition-day pressure. It should read as an instrument of record, not a consumer app: restraint over decoration, clarity over flourish. The existing navy shell with an electric-blue primary, red accent, and gold "current" highlight already carries this register; keep it. Energy belongs on the stage and monitor screens, where the moment earns it, not spread across every form.

## Anti-references

Not a consumer SaaS or startup dashboard — no playful gradients, illustrated mascots, or marketing-y flourishes; this is an official event record. Not generic Bootstrap admin — the flat gray-box default it is being redesigned away from. Not a cluttered broadcast scoreboard — no busy TV overlays or competing animations fighting for attention. Not enterprise gray — no lifeless corporate ERP density with tiny gray text everywhere.

## Design Principles

Fast and mistake-proof on the hot path — the judge-entry screens optimize for speed and large, unambiguous targets so a correct score is quick to enter and a wrong one is hard to submit by accident.

Legible across a hall — the projector monitor and stage screens are designed to be read at distance: high contrast, large type, the current performer and live scores unmistakable at a glance.

One continuous flow — screens reinforce that this is a single event pipeline, not a bag of disconnected forms; state and standings carry through from draw to result without re-entry.

Restraint over decoration — authoritative calm means the default surface is quiet; color and emphasis are spent deliberately (gold for "current", red for the accent moment), never sprinkled.

Light enough for weak clients — effects, motion, and JS stay cheap so underpowered LAN machines and old browsers render fast; nothing critical depends on heavy runtime.

## Accessibility & Inclusion

Target WCAG AA contrast, with the monitor/stage screens pushed beyond AA for hall-distance legibility. Large tap/click targets on the judging screens. Motion must degrade gracefully — honor `prefers-reduced-motion` and never gate content visibility on an animation, since weak clients and headless renders may skip it. Keep the runtime light so underpowered client machines and older browsers stay responsive. Russian is the primary language.
