extends Node


func _ready() -> void:
	var actor := PixelRuntimeActor.new()
	add_child(actor)
	await get_tree().process_frame
	if actor.animated_sprite == null or actor.animated_sprite.sprite_frames == null:
		fail("actor did not build AnimatedSprite2D")
		return
	for direction in ["front", "right", "back", "left"]:
		if not actor.set_direction(direction):
			fail("direction switch failed: " + direction)
			return
		if not actor.animated_sprite.is_playing():
			fail("direction is not playing: " + direction)
			return
		if actor.animated_sprite.sprite_frames.get_frame_count(direction) != 8:
			fail("unexpected frame count: " + direction)
			return
	if actor.animated_sprite.texture_filter != CanvasItem.TEXTURE_FILTER_NEAREST:
		fail("actor texture filter is not nearest")
		return
	var direction_probe := PixelRuntimePlayer.new()
	if direction_probe.direction_for_vector(Vector2.RIGHT) != "left" or direction_probe.direction_for_vector(Vector2.LEFT) != "right":
		fail("horizontal movement is mapped to the wrong facing asset")
		return
	if direction_probe.direction_for_vector(Vector2.DOWN) != "front" or direction_probe.direction_for_vector(Vector2.UP) != "back":
		fail("vertical movement is mapped to the wrong facing asset")
		return
	actor.set_playback_speed(10.0)
	if actor.animated_sprite.sprite_frames.get_animation_speed("front") != 10.0:
		fail("playback speed was not applied")
		return
	print("PIXEL_RUNTIME_ACTOR_PASS directions=4 frames=8 filter=nearest switch=ok")
	get_tree().quit(0)


func fail(message: String) -> void:
	printerr("PIXEL_RUNTIME_ACTOR_FAIL " + message)
	get_tree().quit(1)
