extends Node2D

const ROOT := "res://assets/characters/runtime/chibi_eyes_ears_walk_v1"
const DIRECTIONS := ["front", "right", "back", "left"]
const FRAME_COUNT := 8
const DISPLAY_SCALE := 4.0
const CAPTURE_PATH := "res://test_output/pixel_runtime_scene_capture.png"

var actors: Array[AnimatedSprite2D] = []
var preview_images: Dictionary = {}


func _ready() -> void:
	for index in range(DIRECTIONS.size()):
		var direction: String = DIRECTIONS[index]
		var actor := AnimatedSprite2D.new()
		actor.name = "VisualActor_" + direction
		actor.position = Vector2(120.0 + index * 180.0, 270.0)
		actor.scale = Vector2(DISPLAY_SCALE, DISPLAY_SCALE)
		actor.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		actor.sprite_frames = build_frames(direction)
		actor.animation = "walk"
		actor.frame = index * 2
		add_child(actor)
		actor.play()
		actors.append(actor)

	var image := Image.create(960, 600, false, Image.FORMAT_RGBA8)
	image.fill(Color("20232e"))
	for index in range(actors.size()):
		var actor := actors[index]
		var direction: String = DIRECTIONS[index]
		var frame_image: Image = preview_images[direction][actor.frame].duplicate()
		frame_image.resize(256, 256, Image.INTERPOLATE_NEAREST)
		var target := Vector2i(int(actor.position.x - 128.0), int(actor.position.y - 128.0))
		image.blend_rect(frame_image, Rect2i(Vector2i.ZERO, frame_image.get_size()), target)
	var output_path := ProjectSettings.globalize_path(CAPTURE_PATH)
	var error := image.save_png(output_path)
	if error != OK:
		printerr("PIXEL_RUNTIME_VISUAL_CAPTURE_FAIL error=" + str(error))
		get_tree().quit(1)
		return
	print("PIXEL_RUNTIME_VISUAL_CAPTURE_PASS path=%s size=%dx%d" % [output_path, image.get_width(), image.get_height()])
	get_tree().quit(0)


func _draw() -> void:
	draw_rect(Rect2(0, 0, 960, 600), Color("20232e"))
	draw_line(Vector2(30, 340), Vector2(930, 340), Color("596070"), 2.0)
	for index in range(DIRECTIONS.size()):
		var label_position := Vector2(80.0 + index * 180.0, 390.0)
		draw_string(ThemeDB.fallback_font, label_position, DIRECTIONS[index], HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color("e8eaf0"))


func build_frames(direction: String) -> SpriteFrames:
	var frames := SpriteFrames.new()
	frames.add_animation("walk")
	frames.set_animation_speed("walk", 8.0)
	var source_images: Array[Image] = []
	for frame in range(FRAME_COUNT):
		var path: String = ROOT + "/" + direction + "/frame_%02d/pixel.png" % frame
		var image := Image.load_from_file(ProjectSettings.globalize_path(path))
		if image == null:
			printerr("PIXEL_RUNTIME_VISUAL_CAPTURE_FAIL missing=" + path)
			return frames
		source_images.append(image)
		frames.add_frame("walk", ImageTexture.create_from_image(image))
	preview_images[direction] = source_images
	return frames
