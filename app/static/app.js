/* global deck */
const { Deck, PathLayer, LineLayer, ScatterplotLayer, TripsLayer, DataFilterExtension } = deck;

const ALGOS = {
  dijkstra: { nom: "Dijkstra", couleur: [34, 211, 238] },
  astar:    { nom: "A*",       couleur: [244, 114, 182] },
  greedy:   { nom: "Glouton",  couleur: [251, 191, 36] },
  bfs:      { nom: "BFS",      couleur: [74, 222, 128] },
};
const MODES = {
  pied:    { nom: "piéton", note: "Coût = distance. Toutes les rues et chemins piétons, sans sens interdits." },
  velo:    { nom: "cyclable", note: "Coût = distance. Réseau cyclable OSM, sens uniques respectés." },
  voiture: { nom: "routier", note: "Coût = temps de trajet (limitations de vitesse), sens uniques respectés." },
};
const DUREE_EXPLORATION = 9;   // secondes visées pour l'animation à vitesse ×1
const DUREE_TRACE = 1.6;       // secondes pour dessiner le chemin final

const etat = {
  mode: "pied",
  algo: "dijkstra",
  depart: null,      // [lon, lat]
  arrivee: null,
  prochainClic: "depart",
  reseaux: {},       // mode -> {noeuds: Float64Array, rues}
  resultat: null,
  anim: null,
  multiplicateur: 1,
};

const $ = (s) => document.querySelector(s);
const statut = (t) => { $("#statut").textContent = t || ""; };

// ---------------------------------------------------------------- carte
const vueInitiale = { longitude: 2.3415, latitude: 48.8566, zoom: 12.2, pitch: 0, bearing: 0 };
const carte = new Deck({
  parent: $("#carte"),
  initialViewState: vueInitiale,
  controller: { doubleClickZoom: false },
  getCursor: ({ isDragging }) => (isDragging ? "grabbing" : "crosshair"),
  onClick: (info) => { if (info.coordinate) choisirPoint(etat.prochainClic, info.coordinate, null); },
  layers: [],
});

function calquesRues() {
  const r = etat.reseaux[etat.mode];
  if (!r) return [];
  return [new PathLayer({
    id: "rues-" + etat.mode,
    data: r.rues,
    getPath: (d) => d,
    positionFormat: "XY",
    getColor: [255, 255, 255, 150],
    getWidth: 1,
    widthUnits: "pixels",
    widthMinPixels: 0.6,
    widthMaxPixels: 2,
    jointRounded: false,
  })];
}

function calquesMarqueurs() {
  const pts = [];
  if (etat.depart) pts.push({ p: etat.depart, c: [52, 211, 153] });
  if (etat.arrivee) pts.push({ p: etat.arrivee, c: [248, 113, 113] });
  return [new ScatterplotLayer({
    id: "marqueurs",
    data: pts,
    getPosition: (d) => d.p,
    getFillColor: (d) => d.c,
    getLineColor: [0, 0, 0],
    stroked: true,
    lineWidthMinPixels: 2,
    radiusUnits: "pixels",
    getRadius: 8,
    updateTriggers: { getPosition: [etat.depart, etat.arrivee] },
  })];
}

function calquesAnimation() {
  const a = etat.anim;
  if (!a) return [];
  const exploration = [], fronts = [], chemins = [];
  const filtre = new DataFilterExtension({ filterSize: 1 });
  for (const piste of a.pistes) {
    const c = ALGOS[piste.cle].couleur;
    const pas = Math.min(a.pas, piste.segments.length);
    const fenetre = Math.max(20, a.vitesse * 0.25);
    exploration.push(new LineLayer({
      id: "explo-" + piste.cle,
      data: piste.segments,
      getSourcePosition: (d) => d.s,
      getTargetPosition: (d) => d.t,
      getColor: [...c, a.pistes.length > 1 ? 120 : 150],
      getWidth: 1.6,
      getFilterValue: (d) => d.i,
      filterRange: [0, pas],
      extensions: [filtre],
    }));
    fronts.push(new LineLayer({
      id: "front-" + piste.cle,
      data: piste.segments,
      getSourcePosition: (d) => d.s,
      getTargetPosition: (d) => d.t,
      getColor: [255, 255, 255, 255],
      getWidth: 3,
      getFilterValue: (d) => d.i,
      filterRange: [pas - fenetre, pas],
      extensions: [filtre],
      visible: pas < piste.segments.length,
    }));
    if (piste.trace && piste.progression > 0) {
      chemins.push(new TripsLayer({
        id: "halo-" + piste.cle,
        data: [piste.trace],
        getPath: (d) => d.path,
        getTimestamps: (d) => d.ts,
        getColor: [255, 255, 255],
        opacity: 0.35,
        widthMinPixels: 9,
        capRounded: true, jointRounded: true,
        trailLength: 1e9, fadeTrail: false,
        currentTime: piste.progression,
      }));
      chemins.push(new TripsLayer({
        id: "chemin-" + piste.cle,
        data: [piste.trace],
        getPath: (d) => d.path,
        getTimestamps: (d) => d.ts,
        getColor: c,
        widthMinPixels: 5,
        capRounded: true, jointRounded: true,
        trailLength: 1e9, fadeTrail: false,
        currentTime: piste.progression,
      }));
    }
  }
  return [...exploration, ...fronts, ...chemins];
}

function redessiner() {
  carte.setProps({ layers: [...calquesRues(), ...calquesAnimation(), ...calquesMarqueurs()] });
}

// ---------------------------------------------------------------- réseau
async function chargerReseau(mode) {
  if (!etat.reseaux[mode]) {
    if (mode === etat.mode) statut(`Chargement du réseau ${MODES[mode].nom}…`);
    const rep = await fetch(`/api/reseau/${mode}`);
    if (!rep.ok) { statut("Erreur de chargement du réseau"); return; }
    const d = await rep.json();
    etat.reseaux[mode] = { noeuds: Float64Array.from(d.noeuds), rues: d.rues, nb: d.nb_noeuds, aretes: d.nb_aretes };
  }
  if (mode === etat.mode) {
    const r = etat.reseaux[mode];
    statut(`Réseau ${MODES[mode].nom} : ${r.nb.toLocaleString("fr")} intersections · ${r.aretes.toLocaleString("fr")} tronçons`);
    redessiner();
  }
}

// ---------------------------------------------------------------- saisie
function choisirPoint(cible, lonlat, libelle) {
  etat[cible] = lonlat;
  $(`#in-${cible}`).value = libelle || `${lonlat[1].toFixed(5)}, ${lonlat[0].toFixed(5)} (clic)`;
  etat.prochainClic = cible === "depart" ? "arrivee" : "depart";
  marquerAttente();
  arreterAnimation();
  majBouton();
  redessiner();
}

function marquerAttente() {
  document.querySelectorAll(".champ").forEach((c) =>
    c.classList.toggle("attente", c.dataset.cible === etat.prochainClic));
}

function cadrer() {
  const [a, b] = [etat.depart, etat.arrivee];
  const w = window.innerWidth, h = window.innerHeight;
  const etroit = w < 700;
  const vp = new deck.WebMercatorViewport({ width: w, height: h }).fitBounds(
    [[Math.min(a[0], b[0]), Math.min(a[1], b[1])], [Math.max(a[0], b[0]), Math.max(a[1], b[1])]],
    { padding: etroit ? { left: 30, right: 30, top: 40, bottom: h * 0.58 } : { left: 440, right: 80, top: 80, bottom: 80 } });
  carte.setProps({ initialViewState: { longitude: vp.longitude, latitude: vp.latitude, zoom: Math.min(vp.zoom, 16),
    pitch: 0, bearing: 0, transitionDuration: 800, transitionInterpolator: new deck.FlyToInterpolator() } });
}

function majBouton() { $("#lancer").disabled = !(etat.depart && etat.arrivee); }

document.querySelectorAll(".champ").forEach((champ) => {
  const cible = champ.dataset.cible;
  const input = champ.querySelector("input");
  const liste = champ.querySelector(".suggestions");
  let minuteur, items = [], sel = -1;

  const fermer = () => { liste.classList.remove("ouvert"); sel = -1; };
  const afficher = () => {
    liste.innerHTML = "";
    items.forEach((it, k) => {
      const li = document.createElement("li");
      li.textContent = it.nom.replace(/, France$/, "");
      li.classList.toggle("sel", k === sel);
      li.addEventListener("mousedown", (e) => { e.preventDefault(); valider(k); });
      liste.appendChild(li);
    });
    liste.classList.toggle("ouvert", items.length > 0);
  };
  const valider = (k) => {
    const it = items[k];
    if (!it) return;
    choisirPoint(cible, [it.lon, it.lat], it.nom.split(",").slice(0, 3).join(","));
    fermer();
    carte.setProps({ initialViewState: { ...vueInitiale, longitude: it.lon, latitude: it.lat, zoom: 14,
      transitionDuration: 700, transitionInterpolator: new deck.FlyToInterpolator() } });
  };

  input.addEventListener("focus", () => { etat.prochainClic = cible; marquerAttente(); });
  input.addEventListener("input", () => {
    clearTimeout(minuteur);
    const q = input.value.trim();
    if (q.length < 3) { items = []; afficher(); return; }
    minuteur = setTimeout(async () => {
      try {
        const rep = await fetch(`/api/geocode?q=${encodeURIComponent(q)}`);
        items = rep.ok ? await rep.json() : [];
      } catch { items = []; }
      sel = items.length ? 0 : -1;
      afficher();
    }, 450);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { sel = Math.min(sel + 1, items.length - 1); afficher(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); afficher(); e.preventDefault(); }
    else if (e.key === "Enter") { valider(sel < 0 ? 0 : sel); }
    else if (e.key === "Escape") fermer();
  });
  input.addEventListener("blur", () => setTimeout(fermer, 100));
});

$("#inverser").addEventListener("click", () => {
  [etat.depart, etat.arrivee] = [etat.arrivee, etat.depart];
  const a = $("#in-depart").value; $("#in-depart").value = $("#in-arrivee").value; $("#in-arrivee").value = a;
  arreterAnimation(); redessiner();
});

document.querySelectorAll("#modes button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#modes button").forEach((x) => x.classList.toggle("actif", x === b));
  etat.mode = b.dataset.mode;
  $("#note-mode").textContent = MODES[etat.mode].note;
  arreterAnimation();
  $("#resultats").hidden = true;
  etat.resultat = null;
  redessiner();
  chargerReseau(etat.mode);
}));

document.querySelectorAll("#algos button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#algos button").forEach((x) => x.classList.toggle("actif", x === b));
  etat.algo = b.dataset.algo;
  if (etat.resultat) demarrerAnimation(etat.algo === "tous" ? Object.keys(ALGOS) : [etat.algo]);
}));

$("#vitesse").addEventListener("input", (e) => {
  etat.multiplicateur = 2 ** Number(e.target.value);
  $("#out-vitesse").textContent = "×" + (etat.multiplicateur < 1 ? etat.multiplicateur.toFixed(2).replace(/0$/, "") : etat.multiplicateur);
  if (etat.anim) etat.anim.vitesse = etat.anim.vitesseBase * etat.multiplicateur;
});

// ---------------------------------------------------------------- calcul
$("#lancer").addEventListener("click", async () => {
  const bouton = $("#lancer");
  bouton.disabled = true;
  bouton.textContent = "Calcul en cours…";
  arreterAnimation();
  try {
    await chargerReseau(etat.mode);
    const rep = await fetch("/api/calcul", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: etat.mode, depart: [etat.depart[1], etat.depart[0]], arrivee: [etat.arrivee[1], etat.arrivee[0]] }),
    });
    if (!rep.ok) throw new Error(await rep.text());
    etat.resultat = await rep.json();
    // on recale A et B sur les intersections réellement utilisées
    etat.depart = etat.resultat.depart;
    etat.arrivee = etat.resultat.arrivee;
    afficherTableau();
    cadrer();
    demarrerAnimation(etat.algo === "tous" ? Object.keys(ALGOS) : [etat.algo]);
  } catch (e) {
    console.error(e);
    statut("Erreur pendant le calcul : " + e.message.slice(0, 120));
  } finally {
    bouton.textContent = "Calculer l'itinéraire";
    majBouton();
  }
});

const fmtDist = (m) => (m >= 1000 ? (m / 1000).toFixed(2) + " km" : Math.round(m) + " m");
const fmtTemps = (s) => {
  const min = Math.round(s / 60);
  return min >= 60 ? `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, "0")}` : `${min} min`;
};

function afficherTableau() {
  const r = etat.resultat.resultats;
  const parTemps = etat.resultat.critere === "temps";
  const cout = (x) => (parTemps ? x.temps_s : x.distance_m);
  const ref = cout(r.dijkstra);
  $("#critere").textContent = parTemps ? "— optimisé sur le temps" : "— optimisé sur la distance";
  const tbody = $("#resultats tbody");
  tbody.innerHTML = "";
  for (const [cle, x] of Object.entries(r)) {
    const tr = document.createElement("tr");
    tr.dataset.algo = cle;
    const c = ALGOS[cle].couleur;
    const ecart = x.trouve && ref > 0 ? ((cout(x) - ref) / ref) * 100 : null;
    const ecartTxt = !x.trouve ? "—" : ecart < 0.05 ? '<span class="ok">optimal</span>' : `<span class="ko">+${ecart.toFixed(1)} %</span>`;
    tr.innerHTML = `
      <td><i style="background:rgb(${c})"></i>${x.nom}</td>
      <td>${x.trouve ? fmtDist(x.distance_m) : "aucun"}</td>
      <td>${x.trouve ? fmtTemps(x.temps_s) : "—"}</td>
      <td>${x.nb_explores.toLocaleString("fr")}</td>
      <td>${x.calcul_ms < 10 ? x.calcul_ms.toFixed(1) : Math.round(x.calcul_ms)} ms</td>
      <td>${ecartTxt}</td>`;
    tr.addEventListener("click", () => {
      document.querySelectorAll("#algos button").forEach((b) => b.classList.toggle("actif", b.dataset.algo === cle));
      etat.algo = cle;
      demarrerAnimation([cle]);
    });
    tbody.appendChild(tr);
  }
  $("#resultats").hidden = false;
}

// ---------------------------------------------------------------- animation
function preparerPiste(cle) {
  const x = etat.resultat.resultats[cle];
  const noeuds = etat.reseaux[etat.mode].noeuds;
  const ex = x.explores;
  const segments = new Array(ex.length / 2);
  for (let k = 0; k < segments.length; k++) {
    const p = ex[2 * k], n = ex[2 * k + 1];
    segments[k] = { s: [noeuds[2 * p], noeuds[2 * p + 1]], t: [noeuds[2 * n], noeuds[2 * n + 1]], i: k + 1 };
  }
  let trace = null;
  if (x.geometrie.length > 1) {
    const ts = [0];
    for (let k = 1; k < x.geometrie.length; k++) {
      const [a, b] = [x.geometrie[k - 1], x.geometrie[k]];
      ts.push(ts[k - 1] + Math.hypot((b[0] - a[0]) * Math.cos((a[1] * Math.PI) / 180), b[1] - a[1]));
    }
    const total = ts[ts.length - 1] || 1;
    trace = { path: x.geometrie, ts: ts.map((t) => (t / total) * 1000) };
  }
  return { cle, segments, trace, progression: 0, finExplo: null };
}

function demarrerAnimation(cles) {
  arreterAnimation();
  const pistes = cles.map(preparerPiste);
  const maxSeg = Math.max(...pistes.map((p) => p.segments.length), 1);
  const vitesseBase = Math.max(maxSeg / DUREE_EXPLORATION, 60);
  etat.anim = { pistes, pas: 0, vitesseBase, vitesse: vitesseBase * etat.multiplicateur, dernier: performance.now(), raf: 0 };
  document.querySelectorAll("#resultats tbody tr").forEach((tr) =>
    tr.classList.toggle("actif", cles.length === 1 && tr.dataset.algo === cles[0]));
  $("#compteur").hidden = false;
  const boucle = (t) => {
    const a = etat.anim;
    if (!a) return;
    const dt = Math.min((t - a.dernier) / 1000, 0.1);
    a.dernier = t;
    a.pas += a.vitesse * dt;
    let enCours = false;
    for (const p of a.pistes) {
      if (a.pas >= p.segments.length) {
        if (p.finExplo === null) p.finExplo = t;
        p.progression = Math.min(((t - p.finExplo) / 1000 / DUREE_TRACE) * 1000, 1000);
        if (p.trace && p.progression < 1000) enCours = true;
      } else enCours = true;
    }
    majCompteur();
    redessiner();
    if (enCours) a.raf = requestAnimationFrame(boucle);
  };
  etat.anim.raf = requestAnimationFrame(boucle);
}

function majCompteur() {
  const a = etat.anim;
  const r = etat.resultat.resultats;
  $("#compteur").innerHTML = a.pistes.map((p) => {
    const n = Math.min(Math.floor(a.pas), p.segments.length);
    const fini = n >= p.segments.length;
    const c = ALGOS[p.cle].couleur;
    return `<div><span style="color:rgb(${c})">●</span> <b>${r[p.cle].nom}</b> ${n.toLocaleString("fr")} nœuds ${fini ? (r[p.cle].trouve ? "✓" : "✗") : "…"}</div>`;
  }).join("");
}

function arreterAnimation() {
  if (etat.anim) cancelAnimationFrame(etat.anim.raf);
  etat.anim = null;
  $("#compteur").hidden = true;
}

// ---------------------------------------------------------------- init
$("#note-mode").textContent = MODES[etat.mode].note;
marquerAttente();
chargerReseau("pied").then(() => {
  // précharge les autres réseaux en tâche de fond
  chargerReseau("velo"); chargerReseau("voiture");
});
