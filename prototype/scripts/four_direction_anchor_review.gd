extends Node2D

const FRONT_STAGE := preload("res://scripts/front_arm_swing_stage.gd")
const RIGHT_STAGE := preload("res://scripts/side_arm_swing_stage.gd")
const BACK_STAGE := preload("res://scripts/back_arm_swing_stage.gd")
const LEFT_STAGE := preload("res://scripts/left_mirror_stage.gd")
const FRAME_COUNT := 8
const CENTER_X := 480.0
const FLOOR_Y := 470.0
const DIRECTIONS := ["front", "right", "back", "left"]

var frame_index := 0:
	set(value):
		frame_index = posmod(value, FRAME_COUNT)
		for model in _models.values():
			model.frame_index = frame_index

var _models: Dictionary = {}


func _ready() -> void:
	var constructors := {
		"front": FRONT_STAGE,
		"right": RIGHT_STAGE,
		"back": BACK_STAGE,
		"left": LEFT_STAGE,
	}
	var positions := {
		"front": Vector2(0.0, 0.0),
		"right": Vector2(480.0, 0.0),
		"back": Vector2(0.0, 300.0),
		"left": Vector2(480.0, 300.0),
	}
	for direction in DIRECTIONS:
		var model: Node2D = constructors[direction].new()
		model.position = positions[direction]
		model.scale = Vector2(0.5, 0.5)
		model.frame_index = frame_index
		_models[direction] = model
		add_child(model)


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


func validate_anchor_review() -> PackedStringArray:
	var errors := PackedStringArray()
	var validators := {
		"front": FRONT_STAGE.new().validate_arm_swing(),
		"right": RIGHT_STAGE.new().validate_side_arm_swing(),
		"back": BACK_STAGE.new().validate_back_arm_swing(),
		"left": LEFT_STAGE.new().validate_left_mirror(),
	}
	for direction in DIRECTIONS:
		if not validators[direction].is_empty():
			errors.append("%s stage is not accepted: %s" % [direction, "; ".join(validators[direction])])
		var base := _base_points(direction)
		if base["head"] != Vector2(CENTER_X, 150.0) or base["neck"] != Vector2(CENTER_X, 238.0):
			errors.append("%s head or neck misses the shared registration anchor" % direction)
	for index in range(FRAME_COUNT):
		var pelvis_y: Variant = null
		for direction in DIRECTIONS:
			var pose := _walk_pose(direction, index)
			if not is_equal_approx(pose["pelvis"].x, CENTER_X):
				errors.append("frame %d %s pelvis misses center axis" % [index, direction])
			if pelvis_y == null:
				pelvis_y = pose["pelvis"].y
			elif not is_equal_approx(pose["pelvis"].y, pelvis_y):
				errors.append("frame %d pelvis bob is not registered across directions" % index)
			var feet := [pose["rear_foot"], pose["front_foot"]] if direction in ["right", "left"] else [pose["left_foot"], pose["right_foot"]]
			if feet[0].y > FLOOR_Y or feet[1].y > FLOOR_Y:
				errors.append("frame %d %s foot falls below the shared baseline" % [index, direction])
			if not is_equal_approx(feet[0].y, FLOOR_Y) and not is_equal_approx(feet[1].y, FLOOR_Y):
				errors.append("frame %d %s has no planted foot" % [index, direction])
	return errors
