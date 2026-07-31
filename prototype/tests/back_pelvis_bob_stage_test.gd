extends SceneTree

const MODEL := preload("res://scripts/back_pelvis_bob_stage.gd")
const OUTPUT_DIRECTORY := "res://test_output/skeleton_pipeline/back_pelvis_bob"


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var model := MODEL.new()
	root.add_child(model)
	await process_frame
	var errors := model.validate_back_pelvis_bob()
	if not errors.is_empty():
		_fail("; ".join(errors))
		return
	var directory_path := ProjectSettings.globalize_path(OUTPUT_DIRECTORY)
	DirAccess.make_dir_recursive_absolute(directory_path)
	var directory := DirAccess.open(directory_path)
	if directory == null:
		_fail("could not open output directory")
		return
	for file_name in directory.get_files():
		if file_name.begins_with("frame_") and file_name.ends_with(".png"):
			directory.remove(file_name)
	for index in range(8):
		model.frame_index = index
		await process_frame
		var image := root.get_texture().get_image()
		if image == null or image.is_empty() or image.get_size() != Vector2i(960, 600):
			_fail("frame %d returned an invalid viewport image" % index)
			return
		if image.save_png(directory_path.path_join("frame_%02d.png" % index)) != OK:
			_fail("could not save frame %d" % index)
			return
	print("BACK_PELVIS_BOB_STAGE_PASS frames=8 feet=back_leg_unchanged pelvis=vertical_only output=%s" % directory_path)
	quit(0)


func _fail(message: String) -> void:
	push_error("BACK_PELVIS_BOB_STAGE_FAIL: " + message)
	quit(1)
