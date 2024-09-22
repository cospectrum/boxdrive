{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-utils = {
      url = "github:numtide/flake-utils";
    };
    poetry2nix = {
      inputs.nixpkgs.follows = "nixpkgs";
      url = "github:nix-community/poetry2nix";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      poetry2nix,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        poetryToNix = poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
        poetryApp = poetryToNix.mkPoetryApplication {
          projectDir = ./.;
          preferWheels = true;
        };
      in
      rec {
        apps.default = {
          type = "app";
          program = "${poetryApp}/bin/boxdrive";
        };
        defaultApp = apps.default;
        devShells.default = import ./shell.nix {
          inherit pkgs;
        };
      }
    );
}
