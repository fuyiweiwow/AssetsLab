extends Node2D

const ROOT := "res://assets/characters/runtime/chibi_eyes_ears_walk_v1"
const DIRECTIONS := ["front", "right", "back", "left"]
const SIZE := 64
const FRAME_COUNT := 8

var actors: Array[AnimatedSprite2D] = []


func _ready() -> void:
	for index in range(DIRECTIONS.size()):
		var direction: String = DIRECTIONS[index]
		var actor := AnimatedSprite2D.new()
		actor.name = "Actor_" + direction
		actor.position = Vector2(120.0 + index * 180.0, 280.0)
		actor.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		actor.sprite_frames = build_frames(direction)
		actor.animation = "walk"
		actor.speed_scale = 1.0
		add_child(actor)
		actor.play()
		actors.append(actor)

	await get_tree().process_frame
	for actor in actors:
		if not actor.is_playing():
			fail("animation is not playing: " + actor.name)
			return
		if actor.sprite_frames.get_frame_count("walk") != FRAME_COUNT:
			fail("unexpected frame count: " + actor.name)
			return
		if actor.texture_filter != CanvasItem.TEXTURE_FILTER_NEAREST:
			fail("texture filter is not nearest: " + actor.name)
			return
		if actor.sprite_frames.get_frame_texture("walk", 0).get_width() != SIZE:
			fail("unexpected texture width: " + actor.name)
			return

	print("PIXEL_RUNTIME_SCENE_PASS actors=%d directions=%d frames=%d filter=nearest" % [actors.size(), DIRECTIONS.size(), FRAME_COUNT])
	get_tree().quit(0)


func build_frames(direction: String) -> SpriteFrames:
	var frames := SpriteFrames.new()
	frames.add_animation("walk")
	frames.set_animation_speed("walk", 8.0)
	for frame in range(FRAME_COUNT):
		var path: String = ROOT + "/" + direction + "/frame_%02d/pixel.png" % frame
		var image := Image.load_from_file(ProjectSettings.globalize_path(path))
		if image == null:
			fail("cannot read frame: " + path)
			return frames
		frames.add_frame("walk", ImageTexture.create_from_image(image))
	return frames


func fail(message: String) -> void:
	printerr("PIXEL_RUNTIME_SCENE_FAIL " + message)
	get_tree().quit(1)
