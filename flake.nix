{
  description = "A very basic flake";

  inputs = {
    nixpkgs = {
      type = "github";
      owner = "NixOS";
      repo = "nixpkgs";
      rev = "61c0f513911459945e2cb8bf333dc849f1b976ff"; # nixpkgs-unstable
    };
    flake-utils = {
      url = "github:numtide/flake-utils";
    };
  };
  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config = {
            # allowUnfree = true;
          };
        };
      in
      {
        devShells = {
          default = pkgs.mkShellNoCC {
            packages = with pkgs; [
              git
              uv

              clickhouse
            ];
          };
        };
      }
    );
}
