extends Node2D

const BACK_BASE := preload("res://scripts/back_skeleton_stage.gd")
const PELVIS_STAGE := preload("res://scripts/back_pelvis_bob_stage.gd")
const FRAME_COUNT := 8
const CENTER_X := 480.0
const FLOOR_Y := 470.0
const STATIC_COLOR := Color("5f7c9f")
const REAR_COLOR := Color("7f9fc4")
const FRONT_COLOR := Color("ffd27a")
const ARM_COLOR := Color("a9e8c3")
const JOINT_COLOR := Color("fff1a8")

var frame_index := 0:
	set(value):
		frame_index = posmod(value, FRAME_COUNT)
		queue_redraw()


func back_base_points() -> Dictionary:
	return BACK_BASE.new().back_base_points()


func walk_pose(index: int) -> Dictionary:
	return PELVIS_STAGE.new().walk_pose(index)


func arm_pose(index: int) -> Dictionary:
	var base := back_base_points()
	var phase := TAU * float(posmod(index, FRAME_COUNT)) / float(FRAME_COUNT)
	var left_swing := -sin(phase)
	var right_swing := -left_swing
	return {
		"left_elbow": base["rear_elbow_left"] + Vector2(left_swing * 5.0, left_swing * 6.0),
		"left_hand": base["rear_hand_left"] + Vector2(left_swing * 10.0, left_swing * 14.0),
		"right_elbow": base["rear_elbow_right"] + Vector2(right_swing * 5.0, right_swing * 6.0),
		"right_hand": base["rear_hand_right"] + Vector2(right_swing * 10.0, right_swing * 14.0),
	}


func validate_back_arm_swing() -> PackedStringArray:
	var errors := PackedStringArray()
	var accepted_model := PELVIS_STAGE.new()
	var base := back_base_points()
	for index in range(FRAME_COUNT):
		var pose := walk_pose(index)
		var accepted_pose := accepted_model.walk_pose(index)
		var arms := arm_pose(index)
		for key in ["pelvis", "left_hip", "right_hip", "left_knee", "right_knee", "left_foot", "right_foot", "foreground"]:
			if pose[key] != accepted_pose[key]:
				errors.append("frame %d changes accepted back-pelvis key %s" % [index, key])
		if not (arms["left_hand"] - base["rear_hand_left"]).is_equal_approx(-(arms["right_hand"] - base["rear_hand_right"])):
			errors.append("frame %d back hands are not opposite" % index)
		if not (arms["left_elbow"] - base["rear_elbow_left"]).is_equal_approx(-(arms["right_elbow"] - base["rear_elbow_right"])):
			errors.append("frame %d back elbows are not opposite" % index)
		if arms["left_hand"].y <= base["rear_shoulder_left"].y or arms["right_hand"].y <= base["rear_shoulder_right"].y:
			errors.append("frame %d raises a back hand above its shoulder" % index)
		if arms["left_hand"].x >= CENTER_X or arms["right_hand"].x <= CENTER_X:
			errors.append("frame %d lets a back hand cross the center axis" % index)
		if (arms["left_hand"].x - base["rear_hand_left"].x) * (pose["left_foot"].x - 456.0) > 0.01:
			errors.append("frame %d left back arm is not counterphased to its leg" % index)
	if arm_pose(1)["left_hand"].x >= base["rear_hand_left"].x or arm_pose(5)["left_hand"].x <= base["rear_hand_left"].x:
		errors.append("back left arm does not complete its side swing")
	return errors


func _draw() -> void:
	var base := back_base_points()
	var pose := walk_pose(frame_index)
	var arms := arm_pose(frame_index)
	draw_rect(Rect2(Vector2.ZERO, Vector2(960.0, 600.0)), Color("111827"))
	draw_line(Vector2(160.0, FLOOR_Y), Vector2(800.0, FLOOR_Y), Color("4b5e7a"), 2.0)
	draw_dashed_line(Vector2(CENTER_X, 70.0), Vector2(CENTER_X, 510.0), Color("4b5e7a"), 1.0, 8.0)
	draw_string(ThemeDB.fallback_font, Vector2(710.0, 100.0), "BACK VIEW", HORIZONTAL_ALIGNMENT_LEFT, -1.0, 20, Color("d8b4fe"))
	_bone(base["head"], base["neck"], STATIC_COLOR, 7.0)
	_bone(base["neck"], pose["pelvis"], STATIC_COLOR, 7.0)
	draw_arc(base["head"], 68.0, 0.0, TAU, 48, STATIC_COLOR, 4.0, true)
	_bone(base["rear_shoulder_left"], arms["left_elbow"], ARM_COLOR, 7.0)
	_bone(arms["left_elbow"], arms["left_hand"], ARM_COLOR, 7.0)
	_bone(base["rear_shoulder_right"], arms["right_elbow"], ARM_COLOR, 7.0)
	_bone(arms["right_elbow"], arms["right_hand"], ARM_COLOR, 7.0)
	var rear_leg: String = "right" if pose["foreground"] == "left" else "left"
	_leg(pose, rear_leg, REAR_COLOR)
	_leg(pose, pose["foreground"], FRONT_COLOR)
	draw_circle(pose["pelvis"], 14.0, Color("ffbc73"))
	for key in ["neck", "rear_shoulder_left", "rear_shoulder_right"]:
		draw_circle(base[key], 7.0, JOINT_COLOR)
	for key in ["left_elbow", "left_hand", "right_elbow", "right_hand"]:
		draw_circle(arms[key], 7.0, JOINT_COLOR)
	for key in ["pelvis", "left_hip", "right_hip", "left_knee", "right_knee", "left_foot", "right_foot"]:
		draw_circle(pose[key], 7.0, JOINT_COLOR)


func _bone(from: Vector2, to: Vector2, color: Color, width: float) -> void:
	draw_line(from, to, Color("1d334d"), width + 6.0, true)
	draw_line(from, to, color, width, true)


func _leg(pose: Dictionary, limb: String, color: Color) -> void:
	_bone(pose[limb + "_hip"], pose[limb + "_knee"], color, 8.0)
	_bone(pose[limb + "_knee"], pose[limb + "_foot"], color, 8.0)
