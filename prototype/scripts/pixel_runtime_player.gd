class_name PixelRuntimePlayer
extends CharacterBody2D

signal bomb_requested

@export var move_speed: float = 180.0
@export var walk_fps: float = 8.0

var spawn_position := Vector2.ZERO
var preview_direction := Vector2.ZERO
var runtime_actor: PixelRuntimeActor


func _ready() -> void:
	spawn_position = global_position
	runtime_actor = PixelRuntimeActor.new()
	runtime_actor.position = Vector2(0.0, -26.0)
	runtime_actor.playback_fps = walk_fps
	add_child(runtime_actor)
	var collision := CollisionShape2D.new()
	collision.position = Vector2(0.0, -12.0)
	var shape := RectangleShape2D.new()
	shape.size = Vector2(34.0, 24.0)
	collision.shape = shape
	add_child(collision)


func _physics_process(_delta: float) -> void:
	var input_vector := preview_direction
	if input_vector.is_zero_approx():
		input_vector = _read_keyboard_vector()
	velocity = input_vector * move_speed
	move_and_slide()
	global_position.x = clampf(global_position.x, 28.0, 932.0)
	global_position.y = clampf(global_position.y, 28.0, 572.0)
	if runtime_actor != null and not input_vector.is_zero_approx():
		runtime_actor.set_direction(direction_for_vector(input_vector))


func set_preview_direction(next_direction: Vector2) -> void:
	preview_direction = next_direction.normalized()


func direction_for_vector(input_vector: Vector2) -> String:
	if absf(input_vector.x) > absf(input_vector.y):
		# The Blender side cameras are named from the camera's position. The
		# camera on +X sees the actor's left-facing image, so the runtime asset
		# folders are intentionally opposite to screen-space horizontal input.
		return "left" if input_vector.x > 0.0 else "right"
	return "front" if input_vector.y > 0.0 else "back"


func _read_keyboard_vector() -> Vector2:
	return Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")


func reset_to_spawn() -> void:
	global_position = spawn_position
	velocity = Vector2.ZERO
