class_name PixelRuntimeActor
extends Node2D

@export var asset_root: String = "res://assets/characters/runtime/chibi_eyes_ears_walk_v1"
@export var direction: String = "front"
@export var playback_fps: float = 8.0

var animated_sprite: AnimatedSprite2D
var directions: Array[String] = ["front", "right", "back", "left"]


func _ready() -> void:
	animated_sprite = AnimatedSprite2D.new()
	animated_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(animated_sprite)
	if not build_from_manifest():
		return
	set_direction(direction)


func build_from_manifest() -> bool:
	var manifest_path := asset_root + "/runtime_manifest.json"
	if not FileAccess.file_exists(manifest_path):
		push_error("Missing runtime manifest: " + manifest_path)
		return false
	var file := FileAccess.open(manifest_path, FileAccess.READ)
	var manifest = JSON.parse_string(file.get_as_text())
	if typeof(manifest) != TYPE_DICTIONARY:
		push_error("Invalid runtime manifest: " + manifest_path)
		return false
	directions = []
	for value in manifest.get("directions", []):
		directions.append(str(value))
	var frame_count: int = int(manifest.get("frame_count", 0))
	if directions.is_empty() or frame_count <= 0:
		push_error("Runtime manifest has no animation frames")
		return false

	var frames := SpriteFrames.new()
	for current_direction in directions:
		frames.add_animation(current_direction)
		frames.set_animation_speed(current_direction, playback_fps)
		for frame in range(frame_count):
			var frame_path := asset_root + "/" + current_direction + "/frame_%02d/pixel.png" % frame
			var image := Image.load_from_file(ProjectSettings.globalize_path(frame_path))
			if image == null:
				push_error("Missing runtime frame: " + frame_path)
				return false
			frames.add_frame(current_direction, ImageTexture.create_from_image(image))
	animated_sprite.sprite_frames = frames
	return true


func set_direction(next_direction: String) -> bool:
	if animated_sprite == null or animated_sprite.sprite_frames == null:
		return false
	if not animated_sprite.sprite_frames.has_animation(next_direction):
		return false
	direction = next_direction
	animated_sprite.animation = direction
	animated_sprite.play()
	return true


func set_playback_speed(fps: float) -> void:
	playback_fps = fps
	if animated_sprite == null or animated_sprite.sprite_frames == null:
		return
	for current_direction in directions:
		animated_sprite.sprite_frames.set_animation_speed(current_direction, playback_fps)
