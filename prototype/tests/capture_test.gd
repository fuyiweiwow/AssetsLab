extends SceneTree

const CAPTURE_FPS := 12
const FRAMES_PER_DIRECTION := 9
const START_POSITION := Vector2(128.0, 96.0)
const CAPTURE_DIR := "res://test_output/capture_frames"

var prototype_instance: Node2D
var player: CharacterBody2D
var capture_dir := CAPTURE_DIR
var frame_number := 0
var failed := false


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var pixel_runtime_mode := "--pixel-runtime-actor" in OS.get_cmdline_user_args()
	if pixel_runtime_mode:
		capture_dir = "res://test_output/pixel_runtime_capture_frames"
	_clear_capture_directory()
	var packed_scene := load("res://main.tscn") as PackedScene
	if packed_scene == null:
		_fail("main.tscn could not be loaded")
		return

	prototype_instance = packed_scene.instantiate()
	root.add_child(prototype_instance)
	await process_frame
	await process_frame

	player = prototype_instance.get_node_or_null("Player") as CharacterBody2D
	if player == null:
		_fail("Player node is missing")
		return
	player.global_position = START_POSITION
	if pixel_runtime_mode:
		await _run_pixel_runtime_capture()
		return
	var right_only := "--right-only" in OS.get_cmdline_user_args()
	var vertical_only := "--vertical-only" in OS.get_cmdline_user_args()
	print("CHARACTER_VARIANT=%s" % player.variant)
	print("RGS_WALK_REFERENCE=%s frames=%d" % [player.rgs_walk_reference, player.rgs_walk_reference_frame_textures.size()])
	print("MILESTONE_BODY_RIGHT=%s frames=%d" % [player.milestone_body_right, player.milestone_body_frame_textures.size()])
	print("VERTICAL_BODY_CANDIDATE=%s front=%d back=%d" % [player.vertical_body_candidate, player.vertical_front_frame_textures.size(), player.vertical_back_frame_textures.size()])

	# A vertical-only capture validates the new front/back candidate without
	# mixing it with the current side-direction body resources.
	if vertical_only:
		player._update_direction(Vector2.DOWN)
		player._apply_frame(0)
		await _run_direction(KEY_S, Vector2.DOWN, "S")
		await _run_direction(KEY_W, Vector2.UP, "W")
		_release_all_keys()
		if failed:
			return
		print("CAPTURE_TEST_PASS")
		print("CAPTURE_FRAME_COUNT=%d" % frame_number)
		print("CAPTURE_DIR=%s" % ProjectSettings.globalize_path(capture_dir))
		quit(0)

	# A right-only capture is used for single-direction asset validation so that
	# other direction resources cannot contaminate the GIF.
	if right_only:
		player._update_direction(Vector2.RIGHT)
		player._apply_frame(0)
		await _run_direction(KEY_D, Vector2.RIGHT, "D")
		_release_all_keys()
		if failed:
			return
		print("CAPTURE_TEST_PASS")
		print("CAPTURE_FRAME_COUNT=%d" % frame_number)
		print("CAPTURE_DIR=%s" % ProjectSettings.globalize_path(capture_dir))
		quit(0)

	# Four short segments make one repeatable W/A/S/D walk loop.
	await _run_direction(KEY_D, Vector2.RIGHT, "D")
	await _run_direction(KEY_S, Vector2.DOWN, "S")
	await _run_direction(KEY_A, Vector2.LEFT, "A")
	await _run_direction(KEY_W, Vector2.UP, "W")
	_release_all_keys()

	if failed:
		return
	print("CAPTURE_TEST_PASS")
	print("CAPTURE_FRAME_COUNT=%d" % frame_number)
	print("CAPTURE_DIR=%s" % ProjectSettings.globalize_path(capture_dir))
	quit(0)


func _run_pixel_runtime_capture() -> void:
	var runtime_player = prototype_instance.get_node_or_null("PixelRuntimePlayer")
	if runtime_player == null:
		_fail("PixelRuntimePlayer node is missing")
		return
	var directions := [
		{"vector": Vector2.RIGHT, "label": "D"},
		{"vector": Vector2.DOWN, "label": "S"},
		{"vector": Vector2.LEFT, "label": "A"},
		{"vector": Vector2.UP, "label": "W"},
	]
	for direction_data in directions:
		var start_position: Vector2 = runtime_player.global_position
		runtime_player.set_preview_direction(direction_data["vector"])
		for _frame in range(8):
			await process_frame
			_capture_frame()
		if failed:
			return
		var travelled: Vector2 = runtime_player.global_position - start_position
		if travelled.dot(direction_data["vector"]) < 8.0:
			_fail("runtime actor did not move in expected direction: %s" % direction_data["label"])
			return
		print("PIXEL_RUNTIME_DIRECTION_%s_PASS delta=%s" % [direction_data["label"], travelled])
	runtime_player.set_preview_direction(Vector2.ZERO)
	if failed:
		return
	print("PIXEL_RUNTIME_CAPTURE_PASS directions=4 frames=%d" % frame_number)
	print("PIXEL_RUNTIME_CAPTURE_DIR=%s" % ProjectSettings.globalize_path(capture_dir))
	quit(0)


func _run_direction(keycode: Key, expected_direction: Vector2, label: String) -> void:
	var start_position := player.global_position
	_send_key(keycode, true)
	for _frame in range(FRAMES_PER_DIRECTION):
		await process_frame
		_capture_frame()
	_send_key(keycode, false)
	await process_frame

	var travelled := player.global_position - start_position
	if travelled.dot(expected_direction) < 8.0:
		_fail("%s did not move in the expected direction: %s" % [label, travelled])
		return
	print("DIRECTION_%s_PASS delta=%s" % [label, travelled])


func _send_key(keycode: Key, pressed: bool) -> void:
	var event := InputEventKey.new()
	event.keycode = keycode
	event.physical_keycode = keycode
	event.pressed = pressed
	event.echo = false
	Input.parse_input_event(event)


func _release_all_keys() -> void:
	for keycode in [KEY_W, KEY_A, KEY_S, KEY_D]:
		_send_key(keycode, false)


func _capture_frame() -> void:
	var image: Image
	if "--pixel-runtime-actor" in OS.get_cmdline_user_args():
		image = _build_pixel_runtime_capture()
	else:
		var viewport_texture := root.get_texture()
		if viewport_texture == null:
			_fail("viewport texture is unavailable; run this capture outside --headless")
			return
		image = viewport_texture.get_image()
	if image == null or image.is_empty():
		_fail("viewport returned an empty image")
		return
	var output_path := ProjectSettings.globalize_path("%s/frame_%04d.png" % [capture_dir, frame_number])
	var result := image.save_png(output_path)
	if result != OK:
		_fail("could not save capture frame: %s" % output_path)
		return
	frame_number += 1


func _build_pixel_runtime_capture() -> Image:
	var image := Image.create(960, 600, false, Image.FORMAT_RGBA8)
	image.fill(Color("151a2c"))
	var runtime_player = prototype_instance.get_node_or_null("PixelRuntimePlayer")
	if runtime_player == null or runtime_player.runtime_actor == null:
		return image
	var actor: PixelRuntimeActor = runtime_player.runtime_actor
	var animated_sprite := actor.animated_sprite
	if animated_sprite == null or animated_sprite.sprite_frames == null:
		return image
	var frame_texture := animated_sprite.sprite_frames.get_frame_texture(animated_sprite.animation, animated_sprite.frame)
	if frame_texture == null:
		return image
	var sprite_image := frame_texture.get_image()
	var destination := Vector2i(
		int(round(runtime_player.global_position.x - sprite_image.get_width() * 0.5)),
		int(round(runtime_player.global_position.y - 26.0 - sprite_image.get_height() * 0.5))
	)
	image.blend_rect(sprite_image, Rect2i(Vector2i.ZERO, sprite_image.get_size()), destination)
	return image


func _clear_capture_directory() -> void:
	var directory_path := ProjectSettings.globalize_path(capture_dir)
	DirAccess.make_dir_recursive_absolute(directory_path)
	var directory := DirAccess.open(directory_path)
	if directory == null:
		_fail("could not open capture directory: %s" % directory_path)
		return
	for filename in directory.get_files():
		if filename.ends_with(".png"):
			directory.remove(filename)


func _fail(message: String) -> void:
	if failed:
		return
	failed = true
	_release_all_keys()
	push_error("CAPTURE_TEST_FAIL: " + message)
	quit(1)
