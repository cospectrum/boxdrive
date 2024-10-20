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
        p2n = poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
        poetryScript = "boxdrive";
        poetryOverrides = import ./nix/poetry-overrides.nix { p2n = p2n; };
        preferWheels = true;
        poetryApp = p2n.mkPoetryApplication {
          projectDir = ./.;
          preferWheels = preferWheels;
          overrides = poetryOverrides;
        };
        poetryEnv = p2n.mkPoetryEnv {
          projectDir = ./.;
          preferWheels = preferWheels;
          overrides = poetryOverrides;
        };
      in
      {
        apps.default = {
          type = "app";
          program = "${poetryApp}/bin/${poetryScript}";
        };
        devShells.default = import ./nix/shell.nix {
          inherit pkgs;
          inherit poetryEnv;
        };
      }
    );
}
