# World Compatibility

v0.6.0 generated a map-readable prototype world, but user Windows Minecraft Java load failed. v0.7.0 changes the release definition: generated worlds must pass a real Minecraft Java load smoke.

## What Counts As PASS

- clean world root
- `world_validation.json` valid
- temporary Minecraft server starts with the generated world
- server log reaches `Done`
- no crash reports
- no fatal level.dat, region, or chunk load errors

## What Does Not Count As PASS

- `level.dat` exists
- `session.lock` exists
- `region/r.0.0.mca` exists
- GitHub Actions build succeeds without load smoke

## Target Version

The v0.7.0 Actions smoke uses Minecraft Java server `1.21.1`. If the user opens the world with a different Minecraft version, use the closest compatible Java release and keep a backup of the world folder.
