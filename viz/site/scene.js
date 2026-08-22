/* Scroll-driven flight deck behind the AeroLoop site.

   Everything here is procedural geometry on the vendored Three.js build, so the
   page still opens off the filesystem with no build step and no network. Craft
   are parked on scroll windows: each one enters, crosses the frame and leaves
   as its chapter passes, and idles with its own motion while it is on screen. */

(function () {
  "use strict";

  var canvas = document.getElementById("sky");
  if (!canvas || typeof THREE === "undefined") {
    return;
  }

  var PALETTE = {
    bone: 0xf2e9da,
    paper: 0xfaf4e9,
    ink: 0x12161c,
    navy: 0x16324f,
    petrol: 0x0e5c55,
    orange: 0xe2542c,
    amber: 0xf0a83c,
    sky: 0x9fc7d8,
    lilac: 0xb3a3e0,
    steel: 0xd8cebd
  };

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: true,
    alpha: true,
    powerPreference: "high-performance"
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputEncoding = THREE.sRGBEncoding;

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(42, 1, 0.1, 400);
  camera.position.set(0, 0, 14);

  var clearColor = new THREE.Color(PALETTE.bone);
  var targetClear = new THREE.Color(PALETTE.bone);

  /* ---------------- lighting ---------------- */

  var hemi = new THREE.HemisphereLight(0xffffff, 0x4a4436, 0.72);
  scene.add(hemi);

  var key = new THREE.DirectionalLight(0xffd9ad, 1.15);
  key.position.set(6, 8, 9);
  scene.add(key);

  var rim = new THREE.DirectionalLight(PALETTE.sky, 0.65);
  rim.position.set(-8, -3, -6);
  scene.add(rim);

  var warm = new THREE.PointLight(PALETTE.orange, 0.9, 40);
  warm.position.set(-5, 2, 6);
  scene.add(warm);

  /* ---------------- material helpers ---------------- */

  var fadables = [];

  function mat(color, opts) {
    opts = opts || {};
    var m = new THREE.MeshStandardMaterial({
      color: color,
      roughness: opts.roughness === undefined ? 0.55 : opts.roughness,
      metalness: opts.metalness === undefined ? 0.15 : opts.metalness,
      transparent: true,
      opacity: 1,
      flatShading: !!opts.flat,
      side: opts.side || THREE.FrontSide
    });
    if (opts.emissive) {
      m.emissive = new THREE.Color(opts.emissive);
      m.emissiveIntensity = opts.emissiveIntensity || 1;
    }
    fadables.push(m);
    return m;
  }

  function basic(color, opacity) {
    var m = new THREE.MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: opacity === undefined ? 1 : opacity
    });
    fadables.push(m);
    return m;
  }

  function add(group, geo, material, pos, rot) {
    var mesh = new THREE.Mesh(geo, material);
    if (pos) mesh.position.set(pos[0], pos[1], pos[2]);
    if (rot) mesh.rotation.set(rot[0], rot[1], rot[2]);
    group.add(mesh);
    return mesh;
  }

  /* ---------------- craft ---------------- */

  function buildDrone() {
    var g = new THREE.Group();
    var shell = mat(PALETTE.paper, { roughness: 0.4, metalness: 0.2 });
    var dark = mat(PALETTE.ink, { roughness: 0.45 });
    var accent = mat(PALETTE.orange, { roughness: 0.35 });
    var glass = mat(PALETTE.sky, { roughness: 0.1, metalness: 0.6 });

    add(g, new THREE.BoxBufferGeometry(1.5, 0.42, 1.0), shell, [0, 0, 0]);
    add(g, new THREE.BoxBufferGeometry(0.9, 0.22, 0.62), dark, [0, 0.3, 0]);
    add(g, new THREE.SphereBufferGeometry(0.24, 20, 16), dark, [0.72, -0.12, 0]);
    add(g, new THREE.CylinderBufferGeometry(0.13, 0.13, 0.1, 20), glass, [0.92, -0.12, 0], [0, 0, Math.PI / 2]);

    var rotors = [];
    var armGeo = new THREE.BoxBufferGeometry(2.1, 0.08, 0.12);
    [Math.PI / 4, -Math.PI / 4].forEach(function (a) {
      add(g, armGeo, dark, [0, 0.02, 0], [0, a, 0]);
    });

    var corners = [
      [1, 1],
      [1, -1],
      [-1, 1],
      [-1, -1]
    ];
    corners.forEach(function (c) {
      var ax = c[0] * 0.74;
      var az = c[1] * 0.74;
      add(g, new THREE.CylinderBufferGeometry(0.13, 0.16, 0.22, 14), accent, [ax, 0.08, az]);

      var disc = add(
        g,
        new THREE.CircleBufferGeometry(0.5, 28),
        basic(PALETTE.navy, 0.18),
        [ax, 0.24, az],
        [-Math.PI / 2, 0, 0]
      );
      var hub = new THREE.Group();
      hub.position.set(ax, 0.26, az);
      var bladeGeo = new THREE.BoxBufferGeometry(0.98, 0.02, 0.08);
      var b1 = new THREE.Mesh(bladeGeo, dark);
      var b2 = new THREE.Mesh(bladeGeo, dark);
      b2.rotation.y = Math.PI / 2;
      hub.add(b1);
      hub.add(b2);
      g.add(hub);
      rotors.push(hub);
      disc.renderOrder = 1;
    });

    add(g, new THREE.BoxBufferGeometry(1.3, 0.05, 0.06), dark, [0, -0.34, 0.32]);
    add(g, new THREE.BoxBufferGeometry(1.3, 0.05, 0.06), dark, [0, -0.34, -0.32]);
    add(g, new THREE.BoxBufferGeometry(0.05, 0.28, 0.06), dark, [0.45, -0.2, 0.32]);
    add(g, new THREE.BoxBufferGeometry(0.05, 0.28, 0.06), dark, [-0.45, -0.2, 0.32]);
    add(g, new THREE.BoxBufferGeometry(0.05, 0.28, 0.06), dark, [0.45, -0.2, -0.32]);
    add(g, new THREE.BoxBufferGeometry(0.05, 0.28, 0.06), dark, [-0.45, -0.2, -0.32]);

    g.userData.rotors = rotors;
    return g;
  }

  function buildNacelle() {
    var g = new THREE.Group();
    var skin = mat(PALETTE.paper, { roughness: 0.35, metalness: 0.35 });
    var lip = mat(PALETTE.orange, { roughness: 0.3, metalness: 0.3 });
    var core = mat(PALETTE.ink, { roughness: 0.6 });
    var band = mat(PALETTE.petrol, { roughness: 0.4 });

    add(g, new THREE.CylinderBufferGeometry(1.5, 1.28, 3.4, 40, 1, true), skin, [0, 0, 0], [0, 0, Math.PI / 2]);
    add(g, new THREE.TorusBufferGeometry(1.5, 0.14, 14, 40), lip, [1.7, 0, 0], [0, Math.PI / 2, 0]);
    add(g, new THREE.TorusBufferGeometry(1.3, 0.08, 12, 40), band, [-1.7, 0, 0], [0, Math.PI / 2, 0]);
    add(g, new THREE.CylinderBufferGeometry(0.42, 0.3, 1.1, 20), core, [-1.2, 0, 0], [0, 0, Math.PI / 2]);

    var fan = new THREE.Group();
    fan.position.set(1.2, 0, 0);
    add(fan, new THREE.CylinderBufferGeometry(0.34, 0.34, 0.4, 20), core, [0, 0, 0], [0, 0, Math.PI / 2]);
    var bladeGeo = new THREE.BoxBufferGeometry(0.06, 1.05, 0.28);
    for (var i = 0; i < 14; i++) {
      var b = new THREE.Mesh(bladeGeo, skin);
      var a = (i / 14) * Math.PI * 2;
      b.position.set(0, Math.cos(a) * 0.7, Math.sin(a) * 0.7);
      b.rotation.set(a, 0, 0.32);
      fan.add(b);
    }
    g.add(fan);

    add(g, new THREE.BoxBufferGeometry(0.5, 1.2, 0.3), band, [-0.4, 1.5, 0]);
    g.userData.fan = fan;
    return g;
  }

  function buildRocket() {
    var g = new THREE.Group();
    var body = mat(PALETTE.paper, { roughness: 0.42 });
    var stripe = mat(PALETTE.ink, { roughness: 0.5 });
    var fin = mat(PALETTE.orange, { roughness: 0.4 });

    add(g, new THREE.CylinderBufferGeometry(0.6, 0.6, 4.2, 26), body);
    add(g, new THREE.CylinderBufferGeometry(0.62, 0.62, 0.36, 26), stripe, [0, 1.2, 0]);
    add(g, new THREE.CylinderBufferGeometry(0.62, 0.62, 0.22, 26), fin, [0, -0.7, 0]);
    add(g, new THREE.ConeBufferGeometry(0.6, 1.5, 26), body, [0, 2.85, 0]);
    add(g, new THREE.SphereBufferGeometry(0.12, 12, 10), fin, [0, 3.68, 0]);

    for (var i = 0; i < 3; i++) {
      var a = (i / 3) * Math.PI * 2;
      var f = add(g, new THREE.BoxBufferGeometry(0.1, 1.1, 0.85), fin, [
        Math.cos(a) * 0.62,
        -1.75,
        Math.sin(a) * 0.62
      ]);
      f.rotation.y = -a;
    }

    var flame = new THREE.Mesh(
      new THREE.ConeBufferGeometry(0.5, 2.1, 20, 1, true),
      basic(PALETTE.amber, 0.85)
    );
    flame.position.set(0, -3.2, 0);
    flame.rotation.x = Math.PI;
    g.add(flame);

    var core = new THREE.Mesh(new THREE.ConeBufferGeometry(0.26, 1.2, 16, 1, true), basic(0xfff1cf, 0.95));
    core.position.set(0, -2.8, 0);
    core.rotation.x = Math.PI;
    g.add(core);

    var puffs = [];
    for (var p = 0; p < 4; p++) {
      var puff = new THREE.Mesh(
        new THREE.TorusBufferGeometry(0.5 + p * 0.22, 0.1, 8, 22),
        basic(PALETTE.steel, 0.4 - p * 0.07)
      );
      puff.position.set(0, -3.4 - p * 0.9, 0);
      puff.rotation.x = Math.PI / 2;
      g.add(puff);
      puffs.push(puff);
    }

    g.userData.flame = flame;
    g.userData.core = core;
    g.userData.puffs = puffs;
    return g;
  }

  function buildSatellite() {
    var g = new THREE.Group();
    var body = mat(PALETTE.steel, { roughness: 0.4, metalness: 0.4 });
    var panel = mat(PALETTE.navy, { roughness: 0.25, metalness: 0.6 });
    var trim = mat(PALETTE.amber, { roughness: 0.4 });

    add(g, new THREE.BoxBufferGeometry(1.1, 1.1, 1.4), body);
    add(g, new THREE.CylinderBufferGeometry(0.2, 0.2, 0.4, 14), trim, [0, 0.72, 0]);

    [-1, 1].forEach(function (s) {
      add(g, new THREE.BoxBufferGeometry(0.08, 0.08, 0.9), body, [s * 0.9, 0, 0], [0, Math.PI / 2, 0]);
      var wing = add(g, new THREE.BoxBufferGeometry(2.6, 0.05, 1.1), panel, [s * 2.3, 0, 0]);
      for (var i = 0; i < 4; i++) {
        add(g, new THREE.BoxBufferGeometry(0.04, 0.07, 1.1), trim, [s * (1.3 + i * 0.62), 0.03, 0]);
      }
      wing.rotation.z = s * 0.05;
    });

    var dish = add(g, new THREE.SphereBufferGeometry(0.55, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2.4), body, [
      0,
      0,
      -1.05
    ]);
    dish.rotation.x = Math.PI / 2;
    add(g, new THREE.CylinderBufferGeometry(0.03, 0.03, 0.5, 8), trim, [0, 0, -0.95], [Math.PI / 2, 0, 0]);
    return g;
  }

  function buildCapsule() {
    var g = new THREE.Group();
    var shell = mat(PALETTE.steel, { roughness: 0.38, metalness: 0.45 });
    var hat = mat(PALETTE.paper, { roughness: 0.4 });
    var trim = mat(PALETTE.petrol, { roughness: 0.4 });

    add(g, new THREE.CylinderBufferGeometry(0.95, 1.45, 1.35, 24), shell);
    add(g, new THREE.SphereBufferGeometry(0.95, 24, 14, 0, Math.PI * 2, 0, Math.PI / 2), hat, [0, 0.66, 0]);
    add(g, new THREE.TorusBufferGeometry(1.42, 0.08, 10, 30), trim, [0, -0.6, 0], [Math.PI / 2, 0, 0]);
    for (var i = 0; i < 4; i++) {
      var a = (i / 4) * Math.PI * 2 + Math.PI / 4;
      var leg = add(g, new THREE.CylinderBufferGeometry(0.06, 0.06, 1.5, 8), trim, [
        Math.cos(a) * 1.25,
        -1.2,
        Math.sin(a) * 1.25
      ]);
      leg.rotation.set(Math.sin(a) * 0.38, 0, -Math.cos(a) * 0.38);
      add(g, new THREE.CylinderBufferGeometry(0.24, 0.24, 0.1, 12), shell, [
        Math.cos(a) * 1.55,
        -1.9,
        Math.sin(a) * 1.55
      ]);
    }
    var plume = new THREE.Mesh(new THREE.ConeBufferGeometry(0.55, 1.4, 18, 1, true), basic(PALETTE.orange, 0.5));
    plume.position.set(0, -1.6, 0);
    plume.rotation.x = Math.PI;
    g.add(plume);
    g.userData.plume = plume;
    return g;
  }

  function buildPlanet() {
    var g = new THREE.Group();
    var globe = mat(PALETTE.petrol, { roughness: 0.85, metalness: 0.05 });
    add(g, new THREE.SphereBufferGeometry(3.4, 42, 30), globe);
    var landGeo = new THREE.SphereBufferGeometry(3.42, 24, 18, 0, 1.5, 0.6, 1.1);
    add(g, landGeo, mat(PALETTE.amber, { roughness: 0.9 }));
    var landGeo2 = new THREE.SphereBufferGeometry(3.42, 24, 18, 2.4, 1.1, 1.2, 0.9);
    add(g, landGeo2, mat(PALETTE.orange, { roughness: 0.9 }));
    var ring = add(g, new THREE.TorusBufferGeometry(5.1, 0.16, 12, 90), basic(PALETTE.lilac, 0.55), [0, 0, 0], [
      1.28,
      0.3,
      0
    ]);
    g.userData.ring = ring;
    return g;
  }

  function buildStars() {
    var count = 520;
    var positions = new Float32Array(count * 3);
    for (var i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 90;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 60;
      positions[i * 3 + 2] = -18 - Math.random() * 55;
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    var m = new THREE.PointsMaterial({
      color: 0xfff3dd,
      size: 0.16,
      transparent: true,
      opacity: 0
    });
    var pts = new THREE.Points(geo, m);
    pts.userData.material = m;
    return pts;
  }

  /* ---------------- scroll choreography ---------------- */

  function ease(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  var actors = [];

  function actor(group, spec) {
    scene.add(group);
    group.visible = false;
    actors.push({
      group: group,
      from: spec.from,
      to: spec.to,
      rotFrom: spec.rotFrom || [0, 0, 0],
      rotTo: spec.rotTo || [0, 0, 0],
      scale: spec.scale || 1,
      window: spec.window,
      idle: spec.idle || null,
      fade: spec.fade === undefined ? 0.16 : spec.fade,
      alphaMax: spec.alphaMax === undefined ? 0.82 : spec.alphaMax
    });
    return group;
  }

  var drone = actor(buildDrone(), {
    window: [-0.08, 0.32],
    from: [7.2, -3.4, -0.5],
    to: [4.6, 3.6, -3.0],
    rotFrom: [0.1, -0.6, 0.12],
    rotTo: [-0.12, 0.9, -0.14],
    scale: 1.15,
    idle: function (g, t) {
      g.position.y += Math.sin(t * 1.4) * 0.16;
      g.rotation.z += Math.sin(t * 2.1) * 0.05;
      g.userData.rotors.forEach(function (r, i) {
        r.rotation.y += (i % 2 ? -1 : 1) * 0.5;
      });
    }
  });

  var nacelle = actor(buildNacelle(), {
    window: [0.1, 0.46],
    from: [-8.4, -4.6, -3.0],
    to: [-5.6, 4.4, -6.0],
    rotFrom: [0.25, 0.5, 0.12],
    rotTo: [-0.2, -0.35, -0.1],
    scale: 1.2,
    idle: function (g, t) {
      g.userData.fan.rotation.x = t * 2.4;
      g.position.y += Math.cos(t * 0.8) * 0.2;
    }
  });

  var rocket = actor(buildRocket(), {
    window: [0.3, 0.66],
    from: [-9.6, -10.5, -5.5],
    to: [-8.2, 11.5, -7.5],
    rotFrom: [0, 0, 0.42],
    rotTo: [0, 2.4, -0.16],
    scale: 0.92,
    idle: function (g, t) {
      var f = 1 + Math.sin(t * 22) * 0.16;
      g.userData.flame.scale.set(1, f, 1);
      g.userData.core.scale.set(1, 1 + Math.sin(t * 31) * 0.2, 1);
      g.userData.puffs.forEach(function (p, i) {
        p.rotation.z = t * (0.4 + i * 0.2);
        p.scale.setScalar(1 + Math.sin(t * 1.2 + i) * 0.12);
      });
      g.position.x += Math.sin(t * 0.7) * 0.25;
    }
  });

  var planet = actor(buildPlanet(), {
    window: [0.34, 0.78],
    from: [11.5, -8.5, -18],
    to: [8.5, 5.5, -16],
    rotFrom: [0.2, 0, 0.1],
    rotTo: [0.1, 1.6, 0.16],
    scale: 1,
    fade: 0.22,
    idle: function (g, t) {
      g.rotation.y += 0.0016;
      g.userData.ring.rotation.z = t * 0.06;
    }
  });

  var satellite = actor(buildSatellite(), {
    window: [0.52, 0.86],
    from: [12.4, 7.4, -6.5],
    to: [9.4, -6.2, -8.5],
    rotFrom: [0.3, -0.5, 0.2],
    rotTo: [-0.4, 1.9, -0.3],
    scale: 0.85,
    idle: function (g, t) {
      g.rotation.z += Math.sin(t * 0.6) * 0.004;
      g.position.y += Math.sin(t * 0.9) * 0.22;
    }
  });

  var capsule = actor(buildCapsule(), {
    window: [0.72, 1.0],
    from: [-11.2, 8.0, -6.0],
    to: [-8.8, -5.0, -7.5],
    rotFrom: [0.35, 0.2, 0.35],
    rotTo: [0.06, 2.1, -0.06],
    scale: 0.95,
    idle: function (g, t) {
      g.userData.plume.scale.set(1, 1 + Math.sin(t * 16) * 0.24, 1);
      g.rotation.z += Math.sin(t * 0.8) * 0.004;
    }
  });

  var stars = buildStars();
  scene.add(stars);

  /* ---------------- theme colour from the sections ---------------- */

  var sections = [];

  function indexSections() {
    sections = [];
    var nodes = document.querySelectorAll("section");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      sections.push({
        el: el,
        dark: el.getAttribute("data-theme") === "dark"
      });
    }
  }

  function currentTheme() {
    var probe = window.scrollY + window.innerHeight * 0.5;
    var dark = false;
    for (var i = 0; i < sections.length; i++) {
      var box = sections[i].el;
      var top = box.offsetTop;
      var bottom = top + box.offsetHeight;
      if (probe >= top && probe < bottom) {
        dark = sections[i].dark;
      }
    }
    return dark;
  }

  /* ---------------- loop ---------------- */

  var pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  var scrollP = 0;
  var boost = 0;

  window.addEventListener(
    "pointermove",
    function (e) {
      pointer.tx = (e.clientX / window.innerWidth - 0.5) * 2;
      pointer.ty = (e.clientY / window.innerHeight - 0.5) * 2;
    },
    { passive: true }
  );

  function resize() {
    var w = window.innerWidth;
    var h = window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    var s = Math.min(1, Math.max(0.62, w / 1440));
    actors.forEach(function (a) {
      a.group.scale.setScalar(a.scale * s);
    });
    indexSections();
  }

  window.addEventListener("resize", resize);

  function setOpacity(group, value) {
    group.traverse(function (obj) {
      if (obj.material) {
        obj.material.opacity = obj.material.userData.base === undefined
          ? value
          : value * obj.material.userData.base;
      }
    });
  }

  var clock = new THREE.Clock();

  function frame() {
    requestAnimationFrame(frame);

    var docHeight = Math.max(1, document.body.scrollHeight - window.innerHeight);
    var target = Math.min(1, Math.max(0, window.scrollY / docHeight));
    scrollP += (target - scrollP) * 0.09;

    var t = clock.getElapsedTime();

    pointer.x += (pointer.tx - pointer.x) * 0.05;
    pointer.y += (pointer.ty - pointer.y) * 0.05;
    camera.position.x = pointer.x * 0.9;
    camera.position.y = -pointer.y * 0.6;
    camera.lookAt(0, 0, 0);

    boost *= 0.96;

    for (var i = 0; i < actors.length; i++) {
      var a = actors[i];
      var span = a.window[1] - a.window[0];
      var u = (scrollP - a.window[0]) / span;
      if (u < -0.05 || u > 1.05) {
        a.group.visible = false;
        continue;
      }
      a.group.visible = true;
      var e = ease(Math.min(1, Math.max(0, u)));
      a.group.position.set(
        lerp(a.from[0], a.to[0], e),
        lerp(a.from[1], a.to[1], e),
        lerp(a.from[2], a.to[2], e)
      );
      a.group.rotation.set(
        lerp(a.rotFrom[0], a.rotTo[0], e),
        lerp(a.rotFrom[1], a.rotTo[1], e),
        lerp(a.rotFrom[2], a.rotTo[2], e)
      );
      if (a.idle && !reduceMotion) {
        a.idle(a.group, t);
      }
      var fade = a.fade;
      var alpha = Math.min(1, Math.min(u / fade, (1 - u) / fade));
      setOpacity(a.group, Math.max(0, alpha) * a.alphaMax);
    }

    if (boost > 0.01) {
      drone.rotation.y += boost * 0.4;
      drone.position.y += boost * 0.6;
    }

    var dark = currentTheme();
    targetClear.set(dark ? PALETTE.ink : PALETTE.bone);
    clearColor.lerp(targetClear, 0.06);
    renderer.setClearColor(clearColor, 1);

    stars.userData.material.opacity += ((dark ? 0.85 : 0.0) - stars.userData.material.opacity) * 0.05;
    stars.rotation.y = t * 0.006;
    hemi.intensity = dark ? 0.5 : 0.72;
    warm.intensity = dark ? 1.5 : 0.9;

    renderer.render(scene, camera);
  }

  resize();
  frame();

  /* Small hook so the console can make the drone react when a mission runs. */
  window.AeroSky = {
    kick: function () {
      boost = 1;
    }
  };
})();
