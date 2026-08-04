extends Node2D

# This is deliberately a geometric mannequin, not production pixel art.  It
# turns the accepted joint data into simple filled blocks so later 2D art (or a
# 3D-guided redraw) has one stable, testable motion/registration target.
const ANCHOR_REVIEW := preload("res://scripts/four_direction_anchor_review.gd")
const FRONT_STAGE := preload("res://scripts/front_arm_swing_stage.gd")
const RIGHT_STAGE := preload("res://scripts/side_arm_swing_stage.gd")
const BACK_STAGE := preload("res://scripts/back_arm_swing_stage.gd")
const LEFT_STAGE := preload("res://scripts/left_mirror_stage.gd")
const FRAME_COUNT := 8
const CENTER_X := 480.0
const FLOOR_Y := 470.0
const DISPLAY_SCALE := 0.5
const DIRECTIONS := ["front", "right", "back", "left"]
const ORIGINS := {
	"front": Vector2(0.0, 0.0), "right": Vector2(480.0, 0.0),
	"back": Vector2(0.0, 300.0), "left": Vector2(480.0, 300.0),
}
const OUTLINE := Color("1e293b")
const BODY := Color("cbd5e1")
const REAR_BODY := Color("94a3b8")
const FRONT_BODY := Color("e2e8f0")
const HEAD := Color("f8fafc")
const GUIDE := Color("38bdf8aa")

var frame_index := 0:
	set(value):
		frame_index = posmod(value, FRAME_COUNT)
		queue_redraw()


func _base_points(direction: String) -> Dictionary:
	match direction:
		"front": return FRONT_STAGE.new().front_base_points()
		"right": return RIGHT_STAGE.new().side_base_points()
		"back": return BACK_STAGE.new().back_base_points()
		_: return LEFT_STAGE.new().left_base_points()


func _walk_pose(direction: String, index: int) -> Dictionary:
	match direction:
		"front": return FRONT_STAGE.new().walk_pose(index)
		"right": return RIGHT_STAGE.new().walk_pose(index)
		"back": return BACK_STAGE.new().walk_pose(index)
		_: return LEFT_STAGE.new().walk_pose(index)


func _arm_pose(direction: String, index: int) -> Dictionary:
	match direction:
		"front": return FRONT_STAGE.new().arm_pose(index)
		"right": return RIGHT_STAGE.new().arm_pose(index)
		"back": return BACK_STAGE.new().arm_pose(index)
		_: return LEFT_STAGE.new().arm_pose(index)


func validate_body_blocks() -> PackedStringArray:
	var errors := PackedStringArray()
	var anchor_errors := ANCHOR_REVIEW.new().validate_anchor_review()
	if not anchor_errors.is_empty():
		errors.append_array(anchor_errors)
	for direction in DIRECTIONS:
		var base := _base_points(direction)
		if base["head"] != Vector2(CENTER_X, 150.0) or base["neck"] != Vector2(CENTER_X, 238.0):
			errors.append("%s block head misses the shared anchor" % direction)
		for index in range(FRAME_COUNT):
			var pose := _walk_pose(direction, index)
			var arms := _arm_pose(direction, index)
			var feet := [pose["rear_foot"], pose["front_foot"]] if direction in ["right", "left"] else [pose["left_foot"], pose["right_foot"]]
			if feet[0].y > FLOOR_Y or feet[1].y > FLOOR_Y:
				errors.append("frame %d %s body block falls below the baseline" % [index, direction])
			for hand_key in arms:
				if hand_key.ends_with("hand") and arms[hand_key].y <= base["neck"].y:
					errors.append("frame %d %s block hand rises into the head zone" % [index, direction])
	return errors


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, Vector2(960.0, 600.0)), Color("0f172a"))
	for direction in DIRECTIONS:
		_draw_direction(direction, ORIGINS[direction])


func _draw_direction(direction: String, origin: Vector2) -> void:
	var base := _base_points(direction)
	var pose := _walk_pose(direction, frame_index)
	var arms := _arm_pose(direction, frame_index)
	draw_set_transform(origin, 0.0, Vector2(DISPLAY_SCALE, DISPLAY_SCALE))
	draw_rect(Rect2(Vector2(8.0, 8.0), Vector2(944.0, 584.0)), Color("172554"), false, 3.0)
	draw_line(Vector2(160.0, FLOOR_Y), Vector2(800.0, FLOOR_Y), Color("64748b"), 2.0)
	draw_dashed_line(Vector2(CENTER_X, 74.0), Vector2(CENTER_X, 510.0), Color("334155"), 1.0, 8.0)

	var side_view := direction in ["right", "left"]
	if side_view:
		_draw_limb(base["rear_shoulder"], arms["rear_elbow"], arms["rear_hand"], REAR_BODY)
		var rear_leg: String = "front" if pose["foreground_leg"] == "rear" else "rear"
		_draw_leg(pose, rear_leg, REAR_BODY)
	else:
		_draw_limb(base["shoulder_left"] if direction == "front" else base["rear_shoulder_left"], arms["left_elbow"], arms["left_hand"], BODY)
		_draw_limb(base["shoulder_right"] if direction == "front" else base["rear_shoulder_right"], arms["right_elbow"], arms["right_hand"], BODY)
		var foreground_leg: String = pose["front_leg"] if direction == "front" else pose["foreground"]
		var rear_leg: String = "right" if foreground_leg == "left" else "left"
		_draw_leg(pose, rear_leg, REAR_BODY)

	_draw_torso(base["neck"], pose["pelvis"])
	draw_circle(base["head"], 70.0, OUTLINE)
	draw_circle(base["head"], 63.0, HEAD)

	if side_view:
		_draw_leg(pose, pose["foreground_leg"], FRONT_BODY)
		_draw_limb(base["front_shoulder"], arms["front_elbow"], arms["front_hand"], FRONT_BODY)
	else:
		var frontmost_leg: String = pose["front_leg"] if direction == "front" else pose["foreground"]
		_draw_leg(pose, frontmost_leg, FRONT_BODY)
	_draw_guides(base, pose, arms, direction)
	draw_string(ThemeDB.fallback_font, Vector2(36.0, 64.0), direction.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1.0, 24, Color("bae6fd"))
	draw_set_transform(Vector2.ZERO)


func _draw_torso(neck: Vector2, pelvis: Vector2) -> void:
	draw_line(neck, pelvis, OUTLINE, 106.0, true)
	draw_line(neck, pelvis, BODY, 92.0, true)


func _draw_limb(shoulder: Vector2, elbow: Vector2, hand: Vector2, color: Color) -> void:
	draw_line(shoulder, elbow, OUTLINE, 38.0, true)
	draw_line(elbow, hand, OUTLINE, 38.0, true)
	draw_line(shoulder, elbow, color, 28.0, true)
	draw_line(elbow, hand, color, 28.0, true)
	draw_circle(hand, 18.0, color)


func _draw_leg(pose: Dictionary, limb: String, color: Color) -> void:
	var hip: Vector2 = pose[limb + "_hip"]
	var knee: Vector2 = pose[limb + "_knee"]
	var foot: Vector2 = pose[limb + "_foot"]
	draw_line(hip, knee, OUTLINE, 46.0, true)
	draw_line(knee, foot, OUTLINE, 46.0, true)
	draw_line(hip, knee, color, 34.0, true)
	draw_line(knee, foot, color, 34.0, true)
	draw_circle(foot, 22.0, color)


func _draw_guides(base: Dictionary, pose: Dictionary, arms: Dictionary, direction: String) -> void:
	draw_line(base["neck"], pose["pelvis"], GUIDE, 2.0)
	if direction in ["right", "left"]:
		for key in ["rear_hip", "front_hip", "rear_knee", "front_knee", "rear_foot", "front_foot"]:
			draw_circle(pose[key], 4.0, GUIDE)
	else:
		for key in ["left_hip", "right_hip", "left_knee", "right_knee", "left_foot", "right_foot"]:
			draw_circle(pose[key], 4.0, GUIDE)
	for key in arms:
		draw_circle(arms[key], 4.0, GUIDE)
