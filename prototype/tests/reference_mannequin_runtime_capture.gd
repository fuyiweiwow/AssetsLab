extends SceneTree

const ASSET_ROOT := "res://assets/characters/generated/female_adventurer_reference_mannequin_v1/"
const OUTPUT_ROOT := "res://test_output/reference_mannequin_runtime/"
const DIRECTIONS := ["front", "right", "back", "left"]
const FRAME_COUNT := 8

var sprite: Sprite2D
var frame_number := 0


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	_clear_output()
	_build_scene()
	for direction in DIRECTIONS:
		var texture := load(ASSET_ROOT + direction + ".png") as Texture2D
		if texture == null:
			_fail("missing texture for " + direction)
			return
		if texture.get_width() != 512 or texture.get_height() != 64:
			_fail("unexpected sheet size for %s: %sx%s" % [direction, texture.get_width(), texture.get_height()])
			return
		sprite.texture = texture
		for frame in range(FRAME_COUNT):
			sprite.frame = frame
			await process_frame
			await process_frame
			_capture_frame(direction, frame)
	print("REFERENCE_MANNEQUIN_RUNTIME_CAPTURE_PASS directions=%d frames=%d" % [DIRECTIONS.size(), frame_number])
	quit(0)


func _build_scene() -> void:
	var background := ColorRect.new()
	background.position = Vector2.ZERO
	background.size = Vector2(960, 600)
	background.color = Color("161927")
	background.z_index = -100
	root.add_child(background)

	var rig := Node2D.new()
	rig.position = Vector2(300, 250)
	rig.scale = Vector2(6, 6)
	root.add_child(rig)

	sprite = Sprite2D.new()
	sprite.position = Vector2(32, 32)
	sprite.hframes = FRAME_COUNT
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	rig.add_child(sprite)


func _capture_frame(direction: String, local_frame: int) -> void:
	var image := root.get_viewport().get_texture().get_image()
	if image == null or image.is_empty():
		_fail("viewport returned an empty image")
		return
	var output_path := ProjectSettings.globalize_path(
		"%s%s/frame_%04d.png" % [OUTPUT_ROOT, direction, local_frame]
	)
	DirAccess.make_dir_recursive_absolute(output_path.get_base_dir())
	var result := image.save_png(output_path)
	if result != OK:
		_fail("could not save " + output_path)
		return
	frame_number += 1


func _clear_output() -> void:
	var output_path := ProjectSettings.globalize_path(OUTPUT_ROOT)
	DirAccess.make_dir_recursive_absolute(output_path)
	for direction in DIRECTIONS:
		var directory := DirAccess.open(output_path + direction)
		if directory == null:
			continue
		for filename in directory.get_files():
			if filename.ends_with(".png"):
				directory.remove(filename)


func _fail(message: String) -> void:
	push_error("REFERENCE_MANNEQUIN_RUNTIME_CAPTURE_FAIL: " + message)
	quit(1)
