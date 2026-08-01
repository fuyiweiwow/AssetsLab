extends SceneTree

const FRONT_MODEL := preload("res://scripts/front_arm_swing_stage.gd")
const SIDE_MODEL := preload("res://scripts/side_arm_swing_stage.gd")
const LEFT_MODEL := preload("res://scripts/left_mirror_stage.gd")
const BACK_MODEL := preload("res://scripts/back_arm_swing_stage.gd")
const FRAME_COUNT := 8
const CENTER_X := 480.0
const FLOOR_Y := 470.0
const OUTPUT_PATH := "res://assets/characters/generated/skeleton_walk_pipeline_v1/3d_guide_v1/g1_pose_contract.json"


func _init() -> void:
	call_deferred("_run")


func _round2(value: Vector2) -> Array:
	return [round(value.x * 100.0) / 100.0, round(value.y * 100.0) / 100.0]


func _joint_dict(entries: Array) -> Dictionary:
	var result := {}
	for entry in entries:
		result[entry[0]] = _round2(entry[1])
	return result


func _run() -> void:
	var front := FRONT_MODEL.new()
	var side := SIDE_MODEL.new()
	var left := LEFT_MODEL.new()
	var back := BACK_MODEL.new()
	var errors := front.validate_arm_swing()
	errors.append_array(side.validate_side_arm_swing())
	errors.append_array(left.validate_left_mirror())
	errors.append_array(back.validate_back_arm_swing())
	if not errors.is_empty():
		_fail("accepted model validation failed: " + "; ".join(errors))
		return

	var near_leg: Array[String] = []
	var near_arm: Array[String] = []
	var advance_leg: Array[String] = []
	var frames := []
	for frame_index in range(FRAME_COUNT):
		var front_pose: Dictionary = front.walk_pose(frame_index)
		var front_arms: Dictionary = front.arm_pose(frame_index)
		var front_base: Dictionary = front.front_base_points()
		var side_pose: Dictionary = side.walk_pose(frame_index)
		var side_arms: Dictionary = side.arm_pose(frame_index)
		var side_base: Dictionary = side.side_base_points()
		var left_pose: Dictionary = left.walk_pose(frame_index)
		var left_arms: Dictionary = left.arm_pose(frame_index)
		var left_base: Dictionary = left.left_base_points()
		var back_pose: Dictionary = back.walk_pose(frame_index)
		var back_arms: Dictionary = back.arm_pose(frame_index)
		var back_base: Dictionary = back.back_base_points()
		var phase := TAU * float(frame_index) / float(FRAME_COUNT)
		var left_lift := maxf(0.0, sin(phase))
		var right_lift := maxf(0.0, -sin(phase))
		var front_leg_name: String = "left" if frame_index < 4 else "right"
		near_leg.append(front_leg_name)
		near_arm.append("right" if front_leg_name == "left" else "left")
		advance_leg.append("left" if left_lift > 0.0 else ("right" if right_lift > 0.0 else "none"))
		frames.append({
			"frame": frame_index,
			"front": {
				"joints_2d": _joint_dict([
					["head", front_base["head"]],
					["neck", front_base["neck"]],
					["shoulder_left", front_base["shoulder_left"]],
					["shoulder_right", front_base["shoulder_right"]],
					["elbow_left", front_arms["left_elbow"]],
					["elbow_right", front_arms["right_elbow"]],
					["hand_left", front_arms["left_hand"]],
					["hand_right", front_arms["right_hand"]],
					["pelvis", front_pose["pelvis"]],
					["hip_left", front_pose["left_hip"]],
					["hip_right", front_pose["right_hip"]],
					["knee_left", front_pose["left_knee"]],
					["knee_right", front_pose["right_knee"]],
					["foot_left", front_pose["left_foot"]],
					["foot_right", front_pose["right_foot"]],
				]),
			},
			"right": {
				"joints_2d": _joint_dict([
					["head", side_base["head"]],
					["neck", side_base["neck"]],
					["pelvis", side_pose["pelvis"]],
					["rear_shoulder", side_base["rear_shoulder"]],
					["front_shoulder", side_base["front_shoulder"]],
					["rear_elbow", side_arms["rear_elbow"]],
					["front_elbow", side_arms["front_elbow"]],
					["rear_hand", side_arms["rear_hand"]],
					["front_hand", side_arms["front_hand"]],
					["rear_hip", side_pose["rear_hip"]],
					["front_hip", side_pose["front_hip"]],
					["rear_knee", side_pose["rear_knee"]],
					["front_knee", side_pose["front_knee"]],
					["rear_foot", side_pose["rear_foot"]],
					["front_foot", side_pose["front_foot"]],
				]),
			},
			"back": {
				"joints_2d": _joint_dict([
					["head", back_base["head"]],
					["neck", back_base["neck"]],
					["pelvis", back_pose["pelvis"]],
					["shoulder_left", back_base["rear_shoulder_left"]],
					["shoulder_right", back_base["rear_shoulder_right"]],
					["elbow_left", back_arms["left_elbow"]],
					["elbow_right", back_arms["right_elbow"]],
					["hand_left", back_arms["left_hand"]],
					["hand_right", back_arms["right_hand"]],
					["hip_left", back_pose["left_hip"]],
					["hip_right", back_pose["right_hip"]],
					["knee_left", back_pose["left_knee"]],
					["knee_right", back_pose["right_knee"]],
					["foot_left", back_pose["left_foot"]],
					["foot_right", back_pose["right_foot"]],
				]),
			},
			"left": {
				"joints_2d": _joint_dict([
					["head", left_base["head"]],
					["neck", left_base["neck"]],
					["pelvis", left_pose["pelvis"]],
					["rear_shoulder", left_base["rear_shoulder"]],
					["front_shoulder", left_base["front_shoulder"]],
					["rear_elbow", left_arms["rear_elbow"]],
					["front_elbow", left_arms["front_elbow"]],
					["rear_hand", left_arms["rear_hand"]],
					["front_hand", left_arms["front_hand"]],
					["rear_hip", left_pose["rear_hip"]],
					["front_hip", left_pose["front_hip"]],
					["rear_knee", left_pose["rear_knee"]],
					["front_knee", left_pose["front_knee"]],
					["rear_foot", left_pose["rear_foot"]],
					["front_foot", left_pose["front_foot"]],
				]),
			},
		})

	var contract := {
		"schema": "assetslab_3d_guide_v1_pose_contract",
		"stage": "G1_eight_frame_pose_and_part_masks",
		"generated_by": "prototype/tests/pose_contract_export_test.gd",
		"screen_space": {"canvas": [960, 600], "center_x": CENTER_X, "floor_y": FLOOR_Y, "frame_count": FRAME_COUNT},
		"pose_source": "front",
		"depth_policy": {
			"note": "The 3D guide depth follows the accepted front-view cycle only. The side/back 2D skeletons remain structural references; their limb-depth labels are 2D stylizations and are not re-derived in 3D.",
			"near_leg": near_leg,
			"near_arm": near_arm,
			"advance_leg": advance_leg,
			"constants_3d": {
				"k": 0.015,
				"leg_depth": 0.16,
				"arm_depth": 0.10,
				"foot_advance": 0.45,
				"knee_advance_ratio": 0.45,
				"hand_advance": 0.25,
				"elbow_advance_ratio": 0.5,
			},
		},
		"frames": frames,
	}

	var absolute_path := ProjectSettings.globalize_path(OUTPUT_PATH)
	DirAccess.make_dir_recursive_absolute(absolute_path.get_base_dir())
	var file := FileAccess.open(absolute_path, FileAccess.WRITE)
	if file == null:
		_fail("could not open %s for writing" % absolute_path)
		return
	file.store_string(JSON.stringify(contract, "\t"))
	file.close()
	print("POSE_CONTRACT_EXPORT_PASS frames=32 directions=4 source=front output=%s" % absolute_path)
	quit(0)


func _fail(message: String) -> void:
	push_error("POSE_CONTRACT_EXPORT_FAIL: " + message)
	quit(1)
