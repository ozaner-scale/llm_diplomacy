import * as THREE from "three";
import "./style.css"
import { initMap } from "./map/create";
import { createAnimationsForNextPhase as createAnimationsForNextPhase } from "./units/animate";
import { gameState } from "./gameState";
import { logger } from "./logger";
import { loadBtn, prevBtn, nextBtn, speedSelector, fileInput, playBtn, mapView, loadGameBtnFunction } from "./domElements";
import { updateChatWindows } from "./domElements/chatWindows";
import { initStandingsBoard, hideStandingsBoard, showStandingsBoard } from "./domElements/standingsBoard";
import { displayPhaseWithAnimation, advanceToNextPhase, resetToPhase } from "./phase";
import { config } from "./config";
import { Tween, Group, Easing } from "@tweenjs/tween.js";

//TODO: Create a function that finds a suitable unit location within a given polygon, for placing units better 
//  Currently the location for label, unit, and SC are all the same manually picked location

//const isDebugMode = process.env.NODE_ENV === 'development' || localStorage.getItem('debug') === 'true';
const isDebugMode = config.isDebugMode;
const isStreamingMode = import.meta.env.VITE_STREAMING_MODE

let prevPos


// --- INITIALIZE SCENE ---
function initScene() {
  gameState.initScene()

  // Lighting (keep it simple)
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  gameState.scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
  dirLight.position.set(300, 400, 300);
  gameState.scene.add(dirLight);

  // Initialize standings board
  initStandingsBoard();

  // Load coordinate data, then build the map
  gameState.loadBoardState().then(() => {
    initMap(gameState.scene).then(() => {
      // Update info panel with initial power information
      logger.updateInfoPanel();

      // Only show standings board at startup if no game is loaded
      if (!gameState.gameData || !gameState.gameData.phases || gameState.gameData.phases.length === 0) {
        showStandingsBoard();
      }

      // Load default game file if in debug mode
      if (isDebugMode || isStreamingMode) {
        loadDefaultGameFile();
      }
      if (isStreamingMode) {
        setTimeout(() => {
          togglePlayback()
          gameState.cameraPanAnim = createCameraPan()
        }, 2000)
      }
    })
  }).catch(err => {
    console.error("Error loading coordinates:", err);
    // Use console.error instead of logger.log to avoid updating the info panel
    console.error(`Error loading coords: ${err.message}`);
  });

  // Handle resizing
  window.addEventListener('resize', onWindowResize);

  // Kick off animation loop
  animate();

  // Initialize info panel
  logger.updateInfoPanel();
}

function createCameraPan() {
  // Create a target object to store the desired camera position
  const cameraTarget = { x: gameState.camera.position.x, y: gameState.camera.position.y, z: gameState.camera.position.z };

  // Move from the starting camera position to the left side of the map
  let moveToStartSweepAnim = new Tween(cameraTarget).to({
    x: -400,
    y: 500,
    z: 1000
  }, 8000).onUpdate((target) => {
    // Use smooth interpolation to avoid jumps
    gameState.camera.position.lerp(new THREE.Vector3(target.x, target.y, target.z), 0.1);
  });

  let cameraSweepOperation = new Tween({ timeStep: 0 }).to({
    timeStep: Math.PI
  }, 20000)
    .onUpdate((tweenObj) => {
      let radius = 2200;
      // Calculate the target position
      const targetX = radius * Math.sin(tweenObj.timeStep / 2) - 400;
      const targetY = 500 + 200 * Math.sin(tweenObj.timeStep);
      const targetZ = 1000 + 900 * Math.sin(tweenObj.timeStep);

      // Update the target object
      cameraTarget.x = targetX;
      cameraTarget.y = targetY;
      cameraTarget.z = targetZ;

      // Use smooth interpolation to avoid jumps
      gameState.camera.position.lerp(new THREE.Vector3(targetX, targetY, targetZ), 0.05);
    })
    // .easing(Easing.Quadratic.InOut)
    .yoyo(true).repeat(Infinity);

  moveToStartSweepAnim.chain(cameraSweepOperation);
  moveToStartSweepAnim.start();
  return new Group(moveToStartSweepAnim, cameraSweepOperation);
}

// --- ANIMATION LOOP ---
/*
 * Main animation loop that runs continuously
 * Handles camera movement, animations, and game state transitions
 */
function animate() {
  requestAnimationFrame(animate);

  // Store previous position as a new Vector3 to avoid reference issues
  prevPos = new THREE.Vector3().copy(gameState.camera.position);

  if (gameState.isPlaying) {
    // Update the camera angle
    gameState.cameraPanAnim.update();
  } else {
    // Manual camera controls when not in playback mode
    gameState.camControls.update();
  }

  // Instead of throwing an error, smoothly interpolate if jump is too large
  const jumpThreshold = 20;
  if (Math.abs(prevPos.x - gameState.camera.position.x) > jumpThreshold ||
    Math.abs(prevPos.y - gameState.camera.position.y) > jumpThreshold ||
    Math.abs(prevPos.z - gameState.camera.position.z) > jumpThreshold) {
    console.warn("Large camera position jump detected, smoothing transition");
    // Interpolate to avoid the jump
    gameState.camera.position.lerp(
      new THREE.Vector3(
        prevPos.x + Math.sign(gameState.camera.position.x - prevPos.x) * jumpThreshold,
        gameState.camera.position.y,
        gameState.camera.position.z
      ),
      0.5
    );
  }

  // Check if all animations are complete
  if (gameState.unitAnimations.length > 0) {
    // Filter out completed animations
    const previousCount = gameState.unitAnimations.length;
    gameState.unitAnimations = gameState.unitAnimations.filter(anim => anim.isPlaying());

    // Log when animations complete
    if (previousCount > 0 && gameState.unitAnimations.length === 0) {
      console.log("All unit animations have completed");
    }

    // Call update on each active animation
    gameState.unitAnimations.forEach((anim) => anim.update())

    // If all animations are complete and we're in playback mode
    if (gameState.unitAnimations.length === 0 && gameState.isPlaying && !gameState.messagesPlaying) {
      // Schedule next phase after a pause delay
      console.log(`Scheduling next phase in ${config.playbackSpeed}ms`);
      gameState.playbackTimer = setTimeout(() => advanceToNextPhase(), config.playbackSpeed);
    }
  }

  // Update any pulsing or wave animations on supply centers or units
  if (gameState.scene.userData.animatedObjects) {
    gameState.scene.userData.animatedObjects.forEach(obj => {
      if (obj.userData.pulseAnimation) {
        const anim = obj.userData.pulseAnimation;
        anim.time += anim.speed;
        if (obj.userData.glowMesh) {
          const pulseValue = Math.sin(anim.time) * anim.intensity + 0.5;
          obj.userData.glowMesh.material.opacity = 0.2 + (pulseValue * 0.3);
          obj.userData.glowMesh.scale.set(
            1 + (pulseValue * 0.1),
            1 + (pulseValue * 0.1),
            1 + (pulseValue * 0.1)
          );
        }
        // Subtle bobbing up/down
        obj.position.y = 2 + Math.sin(anim.time) * 0.5;
      }
    });
  }

  gameState.camControls.update();
  gameState.renderer.render(gameState.scene, gameState.camera);
}


// --- RESIZE HANDLER ---
function onWindowResize() {
  gameState.camera.aspect = mapView.clientWidth / mapView.clientHeight;
  gameState.camera.updateProjectionMatrix();
  gameState.renderer.setSize(mapView.clientWidth, mapView.clientHeight);
}

// Load a default game if we're running debug
function loadDefaultGameFile() {
  console.log("Loading default game file for debug mode...");

  // Path to the default game file
  const defaultGameFilePath = './default_game.json';

  fetch(defaultGameFilePath)
    .then(response => {
      if (!response.ok) {
        throw new Error(`Failed to load default game file: ${response.status}`);
      }

      // Check content type to avoid HTML errors
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('text/html')) {
        throw new Error('Received HTML instead of JSON. Check the file path.');
      }

      return response.text();
    })
    .then(data => {
      // Check for HTML content as a fallback
      if (data.trim().startsWith('<!DOCTYPE') || data.trim().startsWith('<html')) {
        throw new Error('Received HTML instead of JSON. Check the file path.');
      }

      console.log("Loaded game file, attempting to parse...");
      return gameState.loadGameData(data);
    })
    .then(() => {
      console.log("Default game file loaded and parsed successfully");
      // Explicitly hide standings board after loading game
      hideStandingsBoard();
    })
    .catch(error => {
      console.error("Error loading default game file:", error);
      // Use console.error instead of logger.log to avoid updating the info panel
      console.error(`Error loading default game: ${error.message}`);

      // Fallback - tell user to drag & drop a file but don't update the info panel
      console.log('Please load a game file using the "Load Game" button.');
    });
}


// --- PLAYBACK CONTROLS ---
function togglePlayback() {
  if (!gameState.gameData || gameState.gameData.phases.length <= 1) return;

  // NEW: If we're speaking, don't allow toggling playback
  if (gameState.isSpeaking) return;

  // Pause the camera animation

  gameState.isPlaying = !gameState.isPlaying;

  if (gameState.isPlaying) {
    playBtn.textContent = "⏸ Pause";
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    logger.log("Starting playback...");

    if (gameState.cameraPanAnim) gameState.cameraPanAnim.getAll()[1].start()
    // Hide standings board when playback starts
    hideStandingsBoard();

    // First, show the messages of the current phase if it's the initial playback
    const phase = gameState.gameData.phases[gameState.phaseIndex];
    if (phase.messages && phase.messages.length) {
      // Show messages with stepwise animation
      logger.log(`Playing ${phase.messages.length} messages from phase ${gameState.phaseIndex + 1}/${gameState.gameData.phases.length}`);
      updateChatWindows(phase, true);
    } else {
      // No messages, go straight to unit animations
      logger.log("No messages for this phase, proceeding to animations");
      displayPhaseWithAnimation();
    }
  } else {
    if (gameState.cameraPanAnim) gameState.cameraPanAnim.getAll()[0].pause();
    playBtn.textContent = "▶ Play";
    if (gameState.playbackTimer) {
      clearTimeout(gameState.playbackTimer);
      gameState.playbackTimer = null;
    }
    gameState.messagesPlaying = false;
    prevBtn.disabled = false;
    nextBtn.disabled = false;
  }
}



// --- EVENT HANDLERS ---
loadBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (file) {
    loadGameBtnFunction(file);
    // Explicitly hide standings board after loading game
    hideStandingsBoard();
  }
});

prevBtn.addEventListener('click', () => {
  if (gameState.phaseIndex > 0) {
    resetToPhase(gameState.phaseIndex - 1)
  }
});
nextBtn.addEventListener('click', () => {
  advanceToNextPhase()
});

playBtn.addEventListener('click', togglePlayback);

speedSelector.addEventListener('change', e => {
  config.playbackSpeed = parseInt(e.target.value);
  // If we're currently playing, restart the timer with the new speed
  if (gameState.isPlaying && gameState.playbackTimer) {
    clearTimeout(gameState.playbackTimer);
    gameState.playbackTimer = setTimeout(() => advanceToNextPhase(), config.playbackSpeed);
  }
});

// --- BOOTSTRAP ON PAGE LOAD ---
window.addEventListener('load', initScene);



