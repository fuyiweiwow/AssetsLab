extends Node2D

const BACK_BASE := preload("res://scripts/back_skeleton_stage.gd")
const LEG_STAGE := preload("res://scripts/back_leg_cycle_stage.gd")
const FRAME_COUNT := 8
const CENTER_X := 480.0
const FLOOR_Y := 470.0
const STATIC_COLOR := Color("5f7c9f")
const REAR_COLOR := Color("7f9fc4")
const FRONT_COLOR := Color("ffd27a")
const JOINT_COLOR := Color("fff1a8")
const PELVIS_OFFSETS := [-2.0, -1.0, 1.0, 3.0, -2.0, -1.0, 1.0, 3.0]

var frame_index := 0:
	set(value):
		frame_index = posmod(value, FRAME_COUNT)
		queue_redraw()


func back_base_points() -> Dictionary:
	return BACK_BASE.new().back_base_points()


func pelvis_offset(index: int) -> float:
	return PELVIS_OFFSETS[posmod(index, FRAME_COUNT)]


func walk_pose(index: int) -> Dictionary:
	var accepted_pose := LEG_STAGE.new().pose(index)
	var offset := Vector2(0.0, pelvis_offset(index))
	accepted_pose["pelvis"] = back_base_points()["pelvis"] + offset
	accepted_pose["left_hip"] += offset
	accepted_pose["right_hip"] += offset
	accepted_pose["left_knee"] += offset * 0.5
	accepted_pose["right_knee"] += offset * 0.5
	return accepted_pose


func validate_back_pelvis_bob() -> PackedStringArray:
	var errors := PackedStringArray()
	var accepted_model := LEG_STAGE.new()
	var base := back_base_points()
	var minimum_offset := INF
	var maximum_offset := -INF
	for index in range(FRAME_COUNT):
		var pose := walk_pose(index)
		var accepted_pose := accepted_model.pose(index)
		var offset := pelvis_offset(index)
		minimum_offset = minf(minimum_offset, offset)
		maximum_offset = maxf(maximum_offset, offset)
		if pose["pelvis"] != base["pelvis"] + Vector2(0.0, offset) or not is_equal_approx(pose["pelvis"].x, CENTER_X):
			errors.append("frame %d has an invalid back pelvis position" % index)
		for key in ["left_foot", "right_foot", "foreground"]:
			if pose[key] != accepted_pose[key]:
				errors.append("frame %d changes accepted back-leg key %s" % [index, key])
		if pose["left_hip"] != accepted_pose["left_hip"] + Vector2(0.0, offset) or pose["right_hip"] != accepted_pose["right_hip"] + Vector2(0.0, offset):
			errors.append("frame %d does not carry both back hips with the pelvis" % index)
		if pose["left_foot"].y > FLOOR_Y or pose["right_foot"].y > FLOOR_Y:
			errors.append("frame %d puts a back foot below the baseline" % index)
		if not is_equal_approx(pose["left_foot"].y, FLOOR_Y) and not is_equal_approx(pose["right_foot"].y, FLOOR_Y):
			errors.append("frame %d has no planted back foot" % index)
	if minimum_offset >= 0.0 or maximum_offset <= 0.0:
		errors.append("back pelvis must travel above and below its base")
	if maximum_offset - minimum_offset > 6.0:
		errors.append("back pelvis bob exceeds the 6px limit")
	return errors


func _draw() -> void:
	var base := back_base_points()
	var pose := walk_pose(frame_index)
	draw_rect(Rect2(Vector2.ZERO, Vector2(960.0, 600.0)), Color("111827"))
	draw_line(Vector2(160.0, FLOOR_Y), Vector2(800.0, FLOOR_Y), Color("4b5e7a"), 2.0)
	draw_dashed_line(Vector2(CENTER_X, 70.0), Vector2(CENTER_X, 510.0), Color("4b5e7a"), 1.0, 8.0)
	draw_string(ThemeDB.fallback_font, Vector2(710.0, 100.0), "BACK VIEW", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 20, Color("d8b4fe"))
	_bone(base["head"], base["neck"], STATIC_COLOR, 7.0)
	_bone(base["neck"], pose["pelvis"], STATIC_COLOR, 7.0)
	draw_arc(base["head"], 68.0, 0.0, TAU, 48, STATIC_COLOR, 4.0, true)
	for side in ["left", "right"]:
		_bone(base["rear_shoulder_" + side], base["rear_elbow_" + side], REAR_COLOR, 7.0)
		_bone(base["rear_elbow_" + side], base["rear_hand_" + side], REAR_COLOR, 7.0)
	var rear_leg: String = "right" if pose["foreground"] == "left" else "left"
	_leg(pose, rear_leg, REAR_COLOR)
	_leg(pose, pose["foreground"], FRONT_COLOR)
	draw_circle(pose["pelvis"], 14.0, Color("ffbc73"))
	for key in ["neck", "rear_shoulder_left", "rear_shoulder_right", "rear_elbow_left", "rear_elbow_right", "rear_hand_left", "rear_hand_right"]:
		draw_circle(base[key], 7.0, JOINT_COLOR)
	for key in ["pelvis", "left_hip", "right_hip", "left_knee", "right_knee", "left_foot", "right_foot"]:
		draw_circle(pose[key], 7.0, JOINT_COLOR)


func _bone(from: Vector2, to: Vector2, color: Color, width: float) -> void:
	draw_line(from, to, Color("1d334d"), width + 6.0, true)
	draw_line(from, to, color, width, true)


func _leg(pose: Dictionary, limb: String, color: Color) -> void:
	_bone(pose[limb + "_hip"], pose[limb + "_knee"], color, 8.0)
	_bone(pose[limb + "_knee"], pose[limb + "_foot"], color, 8.0)
