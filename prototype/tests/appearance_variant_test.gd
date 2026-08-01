extends SceneTree


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene := load("res://main.tscn") as PackedScene
	if packed_scene == null:
		_fail("main.tscn could not be loaded")
		return
	var instance := packed_scene.instantiate()
	root.add_child(instance)
	await process_frame
	var player := instance.get_node_or_null("Player") as CharacterBody2D
	if player == null:
		_fail("Player node is missing")
		return
	var user_args := OS.get_cmdline_user_args()
	if "--base-features" in user_args:
		if not player.base_features:
			_fail("base feature mode was not enabled")
			return
		if player.face_frame_textures.is_empty() or not player.face_frame_textures[0].resource_path.contains("base_features_v1"):
			_fail("base feature face frames were not loaded")
			return
		if player.set_appearance_variant(0):
			_fail("base feature mode accepted generated appearance switching")
			return
		print("APPEARANCE_FIXED_FEATURES_PASS")
		quit(0)
		return

	var selected_variant: int = player.appearance_variant
	if "--appearance-variant=3" in user_args and selected_variant != 3:
		_fail("explicit appearance variant override was not applied")
		return
	if player.face_frame_textures.size() != 32 or player.ear_frame_textures.size() != 32:
		_fail("generated appearance frames were not loaded as 32 frames each")
		return
	if not player.face_frame_textures[0].resource_path.contains("face_%02d" % selected_variant):
		_fail("selected face variant path does not match the selected id")
		return

	var same_seed_a: int = player.appearance_variant_for_seed(123456)
	var same_seed_b: int = player.appearance_variant_for_seed(123456)
	if same_seed_a != same_seed_b:
		_fail("same appearance seed produced different variants")
		return
	var observed := {}
	for seed in range(64):
		observed[player.appearance_variant_for_seed(seed)] = true
	if observed.size() < 4:
		_fail("seeded appearance selection did not cover the male variant pool")
		return

	for variant_id in range(player.APPEARANCE_VARIANT_COUNT):
		if not player.set_appearance_variant(variant_id):
			_fail("could not switch to appearance variant %d" % variant_id)
			return
		if not player.face_frame_textures[0].resource_path.contains("face_%02d" % variant_id):
			_fail("face texture did not switch to appearance variant %d" % variant_id)
			return
		if not player.ear_frame_textures[0].resource_path.contains("ear_%02d" % variant_id):
			_fail("ear texture did not switch to appearance variant %d" % variant_id)
			return

	print("APPEARANCE_VARIANT_PASS variants=%d covered_seeds=%d" % [player.APPEARANCE_VARIANT_COUNT, observed.size()])
	quit(0)


func _fail(message: String) -> void:
	push_error("APPEARANCE_VARIANT_FAIL: " + message)
	quit(1)

