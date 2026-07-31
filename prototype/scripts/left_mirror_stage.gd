extends Node2D

const SIDE_BASE := preload("res://scripts/side_skeleton_stage.gd")
const RIGHT_STAGE := preload("res://scripts/side_arm_swing_stage.gd")
const FRAME_COUNT := 8
const CENTER_X := 480.0
const FLOOR_Y := 470.0
const STATIC_COLOR := Color("5f7c9f")
const REAR_COLOR := Color("7f9fc4")
const FRONT_COLOR := Color("ffd27a")
const ARM_COLOR := Color("a9e8c3")
const JOINT_COLOR := Color("f4f7ff")

var frame_index := 0:
	set(value):
		frame_index = posmod(value, FRAME_COUNT)
		queue_redraw()


func mirror_point(point: Vector2) -> Vector2:
	return Vector2(CENTER_X * 2.0 - point.x, point.y)


func left_base_points() -> Dictionary:
	var base := SIDE_BASE.new().side_base_points()
	for key in base:
		if base[key] is Vector2:
			base[key] = mirror_point(base[key])
	return base


func walk_pose(index: int) -> Dictionary:
	var pose := RIGHT_STAGE.new().walk_pose(index)
	for key in pose:
		if pose[key] is Vector2:
			pose[key] = mirror_point(pose[key])
	return pose


func arm_pose(index: int) -> Dictionary:
	var arms := RIGHT_STAGE.new().arm_pose(index)
	for key in arms:
		arms[key] = mirror_point(arms[key])
	return arms


func validate_left_mirror() -> PackedStringArray:
	var errors := PackedStringArray()
	var right := RIGHT_STAGE.new()
	var source_base := SIDE_BASE.new().side_base_points()
	var left_base := left_base_points()
	for key in source_base:
		if source_base[key] is Vector2 and left_base[key] != mirror_point(source_base[key]):
			errors.append("left base fails to mirror %s" % key)
	if left_base["face_forward"].x >= left_base["head"].x:
		errors.append("left view does not face left")
	for index in range(FRAME_COUNT):
		var source_pose := right.walk_pose(index)
		var left_pose := walk_pose(index)
		for key in ["pelvis", "rear_hip", "front_hip", "rear_knee", "front_knee", "rear_foot", "front_foot"]:
			if left_pose[key] != mirror_point(source_pose[key]):
				errors.append("frame %d fails to mirror walk key %s" % [index, key])
		var source_arms := right.arm_pose(index)
		var left_arms := arm_pose(index)
		for key in ["rear_elbow", "rear_hand", "front_elbow", "front_hand"]:
			if left_arms[key] != mirror_point(source_arms[key]):
				errors.append("frame %d fails to mirror arm key %s" % [index, key])
		if left_pose["rear_foot"].y > FLOOR_Y or left_pose["front_foot"].y > FLOOR_Y:
			errors.append("frame %d puts a left-view foot below the baseline" % index)
		if not is_equal_approx(left_pose["rear_foot"].y, FLOOR_Y) and not is_equal_approx(left_pose["front_foot"].y, FLOOR_Y):
			errors.append("frame %d has no planted left-view foot" % index)
	return errors


func _draw() -> void:
	var base := left_base_points()
	var pose := walk_pose(frame_index)
	var arms := arm_pose(frame_index)
	draw_rect(Rect2(Vector2.ZERO, Vector2(960.0, 600.0)), Color("111827"))
	draw_line(Vector2(160.0, FLOOR_Y), Vector2(800.0, FLOOR_Y), Color("4b5e7a"), 2.0)
	draw_dashed_line(Vector2(CENTER_X, 70.0), Vector2(CENTER_X, 510.0), Color("4b5e7a"), 1.0, 8.0)
	draw_string(ThemeDB.fallback_font, Vector2(710.0, 100.0), "FACING LEFT", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 20, ARM_COLOR)
	draw_line(base["head"], base["face_forward"], ARM_COLOR, 3.0, true)
	draw_colored_polygon(PackedVector2Array([Vector2(412.0, 150.0), Vector2(426.0, 142.0), Vector2(426.0, 158.0)]), ARM_COLOR)
	_bone(base["head"], base["neck"], STATIC_COLOR, 7.0)
	_bone(base["neck"], pose["pelvis"], STATIC_COLOR, 7.0)
	draw_arc(base["head"], 68.0, 0.0, TAU, 48, STATIC_COLOR, 4.0, true)
	_bone(base["rear_shoulder"], arms["rear_elbow"], ARM_COLOR, 7.0)
	_bone(arms["rear_elbow"], arms["rear_hand"], ARM_COLOR, 7.0)
	_bone(base["front_shoulder"], arms["front_elbow"], ARM_COLOR, 7.0)
	_bone(arms["front_elbow"], arms["front_hand"], ARM_COLOR, 7.0)
	var rear_name: String = "front" if pose["foreground_leg"] == "rear" else "rear"
	_leg(pose, rear_name, REAR_COLOR if rear_name == "rear" else FRONT_COLOR)
	_leg(pose, pose["foreground_leg"], FRONT_COLOR if pose["foreground_leg"] == "front" else REAR_COLOR)
	draw_circle(pose["pelvis"], 14.0, Color("ffbc73"))
	for key in ["neck", "rear_shoulder", "front_shoulder"]:
		draw_circle(base[key], 7.0, JOINT_COLOR)
	for key in ["rear_elbow", "rear_hand", "front_elbow", "front_hand"]:
		draw_circle(arms[key], 7.0, JOINT_COLOR)
	for key in ["pelvis", "rear_hip", "front_hip", "rear_knee", "front_knee", "rear_foot", "front_foot"]:
		draw_circle(pose[key], 7.0, JOINT_COLOR)


func _bone(from: Vector2, to: Vector2, color: Color, width: float) -> void:
	draw_line(from, to, Color("1d334d"), width + 6.0, true)
	draw_line(from, to, color, width, true)


func _leg(pose: Dictionary, limb: String, color: Color) -> void:
	_bone(pose[limb + "_hip"], pose[limb + "_knee"], color, 8.0)
	_bone(pose[limb + "_knee"], pose[limb + "_foot"], color, 8.0)
