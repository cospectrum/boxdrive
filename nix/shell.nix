{ pkgs, poetryEnv }:
pkgs.mkShell {
  packages =
    with pkgs;
    [
      poetry
      # fastapi-cli
      (python3.withPackages (
        p: with p; [
          fastapi-cli
        ]
      ))
    ]
    ++ [ poetryEnv ];

  #linkDeps = [ poetryEnv ];
  #LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath linkDeps;
}
