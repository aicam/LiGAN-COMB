import os, struct
import numpy as np
import torch

from . import atom_types, molecules


class AtomStruct(object):
    '''
    A 3D structure of typed atoms and coordinates.
    '''
    def __init__(self, xyz, c, channels, bonds=None, device=None, **info):

        self.check_shapes(xyz, c, channels, bonds)
        self.xyz = torch.as_tensor(xyz, device=device)
        self.c = torch.as_tensor(c, device=device)
        self.channels = channels

        if bonds is not None:
            self.bonds = torch.as_tensor(bonds, device=device)
        else:
            self.bonds = None

        self.info = info

    @staticmethod
    def check_shapes(xyz, c, channels, bonds):
        assert len(xyz.shape) == 2
        assert len(c.shape) == 1
        assert xyz.shape[0] == c.shape[0]
        assert xyz.shape[1] == 3
        assert all(c >= 0) and all(c < len(channels))
        if bonds is not None:
            assert bonds.shape == (xyz.shape[0], xyz.shape[0])

    @classmethod
    def from_gninatypes(cls, gtypes_file, channels, **info):
        xyz, c = read_gninatypes_file(gtypes_file, channels)
        return AtomStruct(xyz, c, channels, **info)

    @classmethod
    def from_coord_set(cls, coord_set, channels, device, **info):
        if not coord_set.has_indexed_types():
            raise ValueError(
                'can only make AtomStruct from CoordinateSet with indexed types'
            )
        xyz = coord_set.coords.tonumpy()
        c = coord_set.type_index.tonumpy().astype(int)
        return cls(
            xyz, c, channels, device=device, src_file=coord_set.src, **info
        )

    @classmethod
    def from_rd_mol(cls, rd_mol, c, channels, **info):
        xyz = rd_mol.GetConformer(0).GetPositions()
        return cls(xyz, c, channels, **info)

    @classmethod
    def from_sdf(cls, sdf_file, channels, **info):
        rd_mol = molecules.read_rd_mols_from_sdf_file(sdf_file)[0]
        channels_file = os.path.splitext(sdf_file)[0] + '.channels'
        c = read_channels_from_file(channels_file, channels)
        return cls.from_rd_mol(rd_mol, c, channels)

    @property
    def n_atoms(self):
        return self.xyz.shape[0]

    @property
    def type_counts(self):
        return atom_types.count_types(self.c, len(self.channels))

    @property
    def center(self):
        assert self.n_atoms > 0
        return self.xyz.mean(dim=0)

    @property
    def radius(self):
        assert self.n_atoms > 0
        return (self.xyz - self.center[None,:]).norm(dim=1).max()

    def to(self, device):
        self.xyz = self.xyz.to(device)
        self.c = self.c.to(device)
        self.bonds = self.bonds.to(device)
    
    def to_ob_mol(self):
        mol = molecules.make_ob_mol(
            self.xyz.float().cpu().numpy(),
            self.c.cpu().numpy(),
            self.bonds.cpu().numpy(),
            self.channels
        )
        return mol

    def to_rd_mol(self):
        mol = molecules.make_rd_mol(
            self.xyz.float().cpu().numpy(),
            self.c.cpu().numpy(),
            self.bonds.cpu().numpy(),
            self.channels
        )
        return mol

    def to_sdf(self, sdf_file):
        if sdf_file.endswith('.gz'):
            outfile = gzip.open(sdf_file, 'wt')
        else:
            outfile = open(sdf_file, 'wt')
        molecules.write_rd_mol_to_sdf_file(outfile, self.to_rd_mol())
        outfile.close()

    def add_bonds(self, tol=0.0):

        atomic_radii = torch.tensor(
            [c.atomic_radius for c in self.channels],
            device=self.c.device
        )
        atom_dist2 = (
            (self.xyz[None,:,:] - self.xyz[:,None,:])**2
        ).sum(axis=2)

        max_bond_dist2 = (
            atomic_radii[self.c][None,:] + atomic_radii[self.c][:,None]
        )
        self.bonds = (atom_dist2 < max_bond_dist2 + tol**2)


def read_gninatypes_file(gtypes_file, channels):
    channel_names = [c.name for c in channels]
    channel_name_idx = {n: i for i, n in enumerate(channel_names)}
    xyz, c = [], []
    with open(gtypes_file, 'rb') as f:
        atom_bytes = f.read(16)
        while atom_bytes:
            x, y, z, t = struct.unpack('fffi', atom_bytes)
            smina_type = atom_types.smina_types[t]
            channel_name = 'Ligand' + smina_type.name
            if channel_name in channel_name_idx:
                c_ = channel_names.index(channel_name)
                xyz.append([x, y, z])
                c.append(c_)
            atom_bytes = f.read(16)
    assert xyz and c, lig_file
    return np.array(xyz), np.array(c)
