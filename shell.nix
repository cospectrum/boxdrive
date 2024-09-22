{ pkgs }:
pkgs.mkShell rec {
  packages = with pkgs; [
    poetry
  ];
}
