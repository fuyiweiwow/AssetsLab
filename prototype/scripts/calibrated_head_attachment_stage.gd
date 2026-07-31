extends "res://scripts/neutral_body_block_stage.gd"

# The head remains registered to the same world-space head/neck anchors while
# the lower body follows its accepted walk and pelvis-bob data.  The cyan guide
# is part of this calibration artifact only; it is not final character art.
const HEAD_RADIUS := 70.0
const NECK_OFFSET := 88.0
const LOCK_COLOR := Color("22d3ee")


func validate_head_attachment() -> PackedStringArray:
	var errors := super.validate_body_blocks()
	for direction in DIRECTIONS:
		var base := _base_points(direction)
		if base["head"] != Vector2(CENTER_X, 150.0):
			errors.append("%s head does not use the calibrated shared anchor" % direction)
		if base["neck"] != Vector2(CENTER_X, 150.0 + NECK_OFFSET):
			errors.append("%s neck does not use the calibrated head offset" % direction)
		if not is_equal_approx(base["head"].distance_to(base["neck"]), NECK_OFFSET):
			errors.append("%s head-to-neck distance is not %dpx" % [direction, NECK_OFFSET])
		for index in range(FRAME_COUNT):
			var pose := _walk_pose(direction, index)
			if pose["pelvis"].y < base["neck"].y + 90.0:
				errors.append("frame %d %s pelvis enters the calibrated head zone" % [index, direction])
	return errors


func _draw() -> void:
	super._draw()
	for direction in DIRECTIONS:
		var base := _base_points(direction)
		draw_set_transform(ORIGINS[direction], 0.0, Vector2(DISPLAY_SCALE, DISPLAY_SCALE))
		draw_arc(base["head"], HEAD_RADIUS + 10.0, 0.0, TAU, 40, LOCK_COLOR, 2.0, true)
		draw_line(base["head"], base["neck"], LOCK_COLOR, 2.0, true)
		draw_circle(base["neck"], 7.0, LOCK_COLOR, false, 2.0)
		draw_string(ThemeDB.fallback_font, Vector2(655.0, 64.0), "HEAD LOCK", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 16, LOCK_COLOR)
		draw_set_transform(Vector2.ZERO)
