extends SceneTree

const ROOT := "res://assets/characters/runtime/chibi_accurig_walk_test_v1"
const DIRECTIONS := ["front", "right", "back", "left"]
const SIZE := 64
const FRAME_COUNT := 8


func _initialize() -> void:
	var manifest_file := FileAccess.open(ROOT + "/runtime_manifest.json", FileAccess.READ)
	if manifest_file == null:
		fail("missing runtime_manifest.json")
		return
	var manifest = JSON.parse_string(manifest_file.get_as_text())
	if typeof(manifest) != TYPE_DICTIONARY:
		fail("invalid manifest json")
		return
	var canvas_px = manifest.get("canvas_px")
	if canvas_px == null or canvas_px.size() != 2 or int(canvas_px[0]) != SIZE or int(canvas_px[1]) != SIZE:
		fail("unexpected canvas size")
		return
	if manifest.get("directions") != DIRECTIONS:
		fail("unexpected directions")
		return
	if manifest.get("frame_count") != FRAME_COUNT:
		fail("unexpected frame count")
		return

	var runtime_frames: SpriteFrames = SpriteFrames.new()
	for direction in DIRECTIONS:
		runtime_frames.add_animation(direction)
		runtime_frames.set_animation_speed(direction, 8.0)
		var sheet_path: String = ROOT + "/" + str(manifest["sprite_sheets"][direction])
		var sheet_image := Image.load_from_file(ProjectSettings.globalize_path(sheet_path))
		if sheet_image == null or sheet_image.get_width() != SIZE * FRAME_COUNT or sheet_image.get_height() != SIZE:
			fail("invalid sheet: " + sheet_path)
			return
		var sheet_texture := ImageTexture.create_from_image(sheet_image)
		if sheet_texture.get_width() != SIZE * FRAME_COUNT or sheet_texture.get_height() != SIZE:
			fail("invalid sheet texture: " + sheet_path)
			return
		for frame in range(FRAME_COUNT):
			var frame_path: String = ROOT + "/" + direction + "/frame_%02d/pixel.png" % frame
			var frame_image := Image.load_from_file(ProjectSettings.globalize_path(frame_path))
			if frame_image == null or frame_image.get_width() != SIZE or frame_image.get_height() != SIZE:
				fail("invalid frame: " + frame_path)
				return
			var frame_texture := ImageTexture.create_from_image(frame_image)
			if frame_texture.get_width() != SIZE or frame_texture.get_height() != SIZE:
				fail("invalid frame texture: " + frame_path)
				return
			runtime_frames.add_frame(direction, frame_texture)

	var animated := AnimatedSprite2D.new()
	animated.sprite_frames = runtime_frames
	animated.animation = "right"
	animated.frame = 3
	animated.play()
	if not animated.is_playing() or animated.sprite_frames.get_frame_count("right") != FRAME_COUNT:
		fail("AnimatedSprite2D did not start the right-facing walk")
		return

	animated.free()
	runtime_frames = null
	print("PIXEL_RUNTIME_GODOT_FILE_PASS directions=%d frames=%d size=%d" % [DIRECTIONS.size(), DIRECTIONS.size() * FRAME_COUNT, SIZE])
	print("PIXEL_RUNTIME_GODOT_ANIMATEDSPRITE_PASS animation=right frames=%d" % FRAME_COUNT)
	quit(0)


func fail(message: String) -> void:
	printerr("PIXEL_RUNTIME_GODOT_IMPORT_FAIL " + message)
	quit(1)
