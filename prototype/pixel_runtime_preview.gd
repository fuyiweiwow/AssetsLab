extends Node2D

const ROOT := "res://assets/characters/runtime/chibi_accurig_walk_test_v1"
const DIRECTIONS := ["front", "right", "back", "left"]
const FRAME_COUNT := 8
const DISPLAY_SCALE := 4.0

var actors: Array[AnimatedSprite2D] = []


func _ready() -> void:
	_build_preview()
	if "--validate-only" in OS.get_cmdline_user_args():
		await get_tree().process_frame
		_validate_imported_scene()


func _build_preview() -> void:
	for index in range(DIRECTIONS.size()):
		var direction: String = DIRECTIONS[index]
		var actor := AnimatedSprite2D.new()
		actor.name = "ImportedActor_" + direction
		actor.position = Vector2(120.0 + index * 180.0, 270.0)
		actor.scale = Vector2(DISPLAY_SCALE, DISPLAY_SCALE)
		actor.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		actor.sprite_frames = _build_frames(direction)
		actor.animation = "walk"
		actor.frame = index * 2
		add_child(actor)
		actor.play()
		actors.append(actor)


func _build_frames(direction: String) -> SpriteFrames:
	var frames := SpriteFrames.new()
	frames.add_animation("walk")
	frames.set_animation_speed("walk", 8.0)
	for frame in range(FRAME_COUNT):
		var path := "%s/%s/frame_%02d/pixel.png" % [ROOT, direction, frame]
		var texture := load(path) as Texture2D
		if texture == null:
			push_error("PIXEL_RUNTIME_PREVIEW_FAIL missing imported texture: " + path)
			continue
		frames.add_frame("walk", texture)
	return frames


func _validate_imported_scene() -> void:
	for actor in actors:
		if not actor.is_playing():
			_fail("animation is not playing: " + actor.name)
			return
		if actor.sprite_frames == null or actor.sprite_frames.get_frame_count("walk") != FRAME_COUNT:
			_fail("unexpected frame count: " + actor.name)
			return
		if actor.texture_filter != CanvasItem.TEXTURE_FILTER_NEAREST:
			_fail("texture filter is not nearest: " + actor.name)
			return
		var texture := actor.sprite_frames.get_frame_texture("walk", 0)
		if texture == null or texture.get_width() != 64 or texture.get_height() != 64:
			_fail("unexpected imported texture size: " + actor.name)
			return
	print("PIXEL_RUNTIME_IMPORTED_SCENE_PASS actors=%d directions=%d frames=%d filter=nearest" % [actors.size(), DIRECTIONS.size(), FRAME_COUNT])
	get_tree().quit(0)


func _fail(message: String) -> void:
	printerr("PIXEL_RUNTIME_IMPORTED_SCENE_FAIL " + message)
	get_tree().quit(1)


func _draw() -> void:
	draw_rect(Rect2(0.0, 0.0, 960.0, 600.0), Color("151a2c"))
	draw_string(ThemeDB.fallback_font, Vector2(32.0, 42.0), "Pixel Runtime Imported Preview", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 24, Color("e8eaf0"))
	draw_string(ThemeDB.fallback_font, Vector2(32.0, 70.0), "Godot imported PNG + AnimatedSprite2D + nearest filter", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 16, Color("aeb6cc"))
	for index in range(DIRECTIONS.size()):
		var center_x := 120.0 + index * 180.0
		draw_line(Vector2(center_x - 64.0, 350.0), Vector2(center_x + 64.0, 350.0), Color("596070"), 2.0)
		draw_string(ThemeDB.fallback_font, Vector2(center_x - 32.0, 390.0), DIRECTIONS[index], HORIZONTAL_ALIGNMENT_LEFT, -1.0, 18, Color("e8eaf0"))
